import os
import requests
import time

def sanitize_filename(filename):
    """Sanitize a filename to remove invalid characters."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).strip()

def download_ts_segments(base_url, temp_folder, retries=3, backoff=2):
    """
    Download sequential .ts segments by incrementing the segment number in the URL.
    Only increments the part before `.ts`, leaving query parameters unchanged.
    """
    os.makedirs(temp_folder, exist_ok=True)
    segment_number = 0
    failed_attempts = 0
    ts_files = []

    print("Starting download...")
    while True:
        # Format the segment number with leading zeros (e.g., 000000)
        segment_str = f"{segment_number:06d}"
        # Replace the segment part in the URL
        url = base_url.replace("-000000.ts", f"-{segment_str}.ts")
        success = False

        for attempt in range(retries):
            try:
                print(f"Downloading {url} (Attempt {attempt + 1}/{retries})...")
                response = requests.get(url, stream=True, timeout=10)
                if response.status_code == 200:
                    # Save the file
                    sanitized_filename = sanitize_filename(f"{segment_str}.ts")
                    file_path = os.path.join(temp_folder, sanitized_filename)
                    with open(file_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                    ts_files.append(file_path)
                    print(f"Downloaded: {file_path}")
                    success = True
                    failed_attempts = 0  # Reset on success
                    break  # Exit retry loop
                else:
                    print(f"Failed to download: {url} (Status code: {response.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {url}: {e}")
            
            # Retry logic
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
        
        if not success:
            failed_attempts += 1
            print(f"Failed to download {url} after {retries} retries.")
            if failed_attempts >= 5:  # Stop after 5 consecutive failures
                print("Reached maximum consecutive failures. Stopping.")
                break
        
        # Increment the segment number
        segment_number += 1

    return ts_files

def create_ffmpeg_file_list(ts_files, temp_folder):
    """Create a file list for FFmpeg with only the base filenames."""
    list_file_path = os.path.join(temp_folder, "file_list.txt")
    with open(list_file_path, 'w') as file:
        for ts_file in ts_files:
            base_filename = os.path.basename(ts_file)  # Extract only the filename
            file.write(f"file '{base_filename}'\n")
    print(f"Created FFmpeg file list at {list_file_path}")
    return list_file_path

def combine_ts_files_ffmpeg(file_list_path, output_file):
    """Combine .ts files into a single video using FFmpeg."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.system(f"ffmpeg -f concat -safe 0 -i \"{file_list_path}\" -c copy \"{output_file}\"")
    print(f"Combined .ts files into {output_file}")

def cleanup_ts_files(ts_folder):
    """Delete all .ts files in the specified folder."""
    for ts_file in os.listdir(ts_folder):
        if ts_file.endswith('.ts'):
            os.remove(os.path.join(ts_folder, ts_file))
    print("All .ts files have been deleted.")

if __name__ == "__main__":
    # Input base URL and video output name
    base_url = input("Enter the full URL with -000000.ts segment (e.g., ...-000000.ts): ").strip()
    output_file_name = input("Enter output video file name (with extension, e.g., video.mp4): ").strip()
    
    # Set default output file name if none is provided
    if not output_file_name:
        output_file_name = "combined_video.mp4"

    # Define folders
    temp_folder = "temp_files"
    output_folder = "output_video"
    output_video_path = os.path.join(output_folder, output_file_name)

    # Download .ts segments
    ts_files = download_ts_segments(base_url, temp_folder)
    
    if ts_files:
        # Create FFmpeg file list
        ffmpeg_file_list = create_ffmpeg_file_list(ts_files, temp_folder)
        
        # Combine .ts files
        combine_ts_files_ffmpeg(ffmpeg_file_list, output_video_path)
        
        # Clean up .ts files
        cleanup_ts_files(temp_folder)
    else:
        print("No .ts files were downloaded.")
