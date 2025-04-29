import os
import time
from datetime import datetime
import re # Import regular expression module for sanitizing filenames
import base64 # May be needed for some CDP methods if used later

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
# from selenium.webdriver.firefox.service import Service as FirefoxService # For Firefox
# from selenium.webdriver.firefox.options import Options as FirefoxOptions # For Firefox

# --- Google API Imports ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- Image Conversion ---
from PIL import Image # For converting PNG to JPG

# --- Configuration Source ---
CONFIG_SPREADSHEET_ID = '19pnGhmC1CXEN9RtXhs64ahvFcggW18S9ZUZyos1T3Lw' # Fixed Sheet ID for config
CONFIG_SHEET_NAME = 'CONFIG' # Tab name containing the job list
EXPECTED_HEADERS = ['Capture Date', 'Image URL', 'HTML Copy'] # Headers for target sheets

# --- Google API Configuration ---
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',    # Drive API for uploads
    'https://www.googleapis.com/auth/spreadsheets' # Sheets API for logging & config & sheet creation
]
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# --- Other Configuration ---
LOCAL_SAVE_DIR = 'temp_web_captures'
RUN_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Helper Function: Google Authentication (Handles Both Drive & Sheets) ---
def get_authenticated_services():
    """Authenticates and returns Google Drive and Sheets service objects."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except ValueError as e:
             print(f"Error loading token file ({TOKEN_FILE}): {e}. Likely due to scope changes. Re-authentication needed.")
             creds = None
        except Exception as e:
             print(f"Unexpected error loading token file ({TOKEN_FILE}): {e}. Re-authentication may be needed.")
             creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}. Re-authentication needed.")
                if os.path.exists(TOKEN_FILE):
                    try: os.remove(TOKEN_FILE); print(f"Deleted invalid/expired token file: {TOKEN_FILE}")
                    except OSError as del_e: print(f"Error deleting token file {TOKEN_FILE}: {del_e}")
                creds = None
        else:
             creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"ERROR: Credentials file '{CREDENTIALS_FILE}' not found.")
                return None, None
            try:
                print(f"Performing new authentication (Scopes: {SCOPES})...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                print("\nA browser window will open for Google authentication.")
                print("Please log in with the Google account that has access to the target Drive folders and Sheet(s).")
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
                print(f"Authentication successful. Credentials saved to {TOKEN_FILE}")
            except Exception as e:
                print(f"Error during authentication flow: {e}")
                return None, None

    try:
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        print("Google Drive and Sheets services created successfully.")
        return drive_service, sheets_service
    except HttpError as error:
        print(f'An error occurred building Google services: {error}')
        return None, None
    except Exception as e:
         print(f"An unexpected error occurred building services: {e}")
         return None, None

# --- Helper Function: Upload File to Google Drive (Returns File ID and Link) ---
def upload_to_drive(service, local_filepath, filename_on_drive, folder_id, mime_type):
    """Uploads a file to Google Drive and returns the file ID and webViewLink."""
    if not service: print("Drive service not available. Skipping upload."); return None, None
    if not os.path.exists(local_filepath): print(f"Local file not found: {local_filepath}. Skipping upload."); return None, None
    try:
        file_metadata = {'name': filename_on_drive, 'parents': [folder_id]}
        media = MediaFileUpload(local_filepath, mimetype=mime_type, resumable=True)
        print(f"Uploading '{filename_on_drive}' to Drive Folder ID: {folder_id}...")
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        file_id = file.get('id'); file_link = file.get('webViewLink')
        print(f"Successfully uploaded '{filename_on_drive}' (ID: {file_id})")
        return file_id, file_link
    except HttpError as error:
        print(f"An error occurred during upload of '{filename_on_drive}': {error}")
        if error.resp.status == 404: print(f"Error Detail: Google Drive Folder ID '{folder_id}' not found or permission denied.")
        elif error.resp.status == 403: print(f"Error Detail: Permission denied for uploading to folder '{folder_id}'.")
        return None, None
    except Exception as e: print(f"An unexpected error occurred during upload of '{filename_on_drive}': {e}"); return None, None

# --- Helper Function: Get Jobs from Config Sheet ---
def get_jobs_from_sheet(service, spreadsheet_id, config_sheet_name='CONFIG'):
    """Reads job configurations from the specified sheet."""
    jobs = []
    if not service: print("Sheets service not available. Cannot fetch jobs."); return jobs
    try:
        range_to_read = f"{config_sheet_name}!A2:C"
        print(f"Reading job configurations from Sheet ID '{spreadsheet_id}', Tab '{config_sheet_name}'...")
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_to_read).execute()
        values = result.get('values', [])
        if not values: print(f"No job configurations found in '{config_sheet_name}'.")
        else:
            print(f"Found {len(values)} potential jobs.")
            for i, row in enumerate(values):
                if len(row) >= 3:
                    url = row[0].strip(); folder_id = row[1].strip(); sheet_name = row[2].strip()
                    if url and folder_id and sheet_name: jobs.append({"url": url, "folder_id": folder_id, "sheet_name": sheet_name})
                    else: print(f"Warning: Skipping row {i+2} in '{config_sheet_name}' due to missing data.")
                else: print(f"Warning: Skipping row {i+2} in '{config_sheet_name}' because it has fewer than 3 columns.")
            print(f"Successfully parsed {len(jobs)} valid jobs.")
    except HttpError as error:
        print(f"An error occurred reading the config sheet '{config_sheet_name}': {error}"); error_details = error.content.decode() if error.content else ""
        if error.resp.status == 400 and 'Unable to parse range' in error_details: print(f"**ACTION:** Ensure the tab named '{config_sheet_name}' exists in Spreadsheet ID '{spreadsheet_id}'.")
        elif error.resp.status == 403: print(f"**ACTION:** Ensure the authenticated user has VIEW permission for Spreadsheet ID '{spreadsheet_id}'.")
    except Exception as e: print(f"An unexpected error occurred while fetching jobs: {e}")
    return jobs

# --- Helper Function: Ensure Sheet Exists (Creates if not) ---
def ensure_sheet_exists(service, spreadsheet_id, sheet_name):
    """Checks if a sheet exists, creates it if not. Returns True if exists/created, False on error."""
    if not service: return False
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields='sheets(properties(title))').execute()
        sheets = sheet_metadata.get('sheets', '')
        for sheet in sheets:
            if sheet.get('properties', {}).get('title') == sheet_name: return True
        print(f"Target sheet '{sheet_name}' not found. Creating it...")
        body = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        response = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        print(f"Successfully created sheet '{sheet_name}'."); return True
    except HttpError as error: print(f"An error occurred checking/creating sheet '{sheet_name}': {error}"); return False
    except Exception as e: print(f"An unexpected error occurred during sheet check/creation: {e}"); return False

# --- Helper Function: Ensure Headers Exist in Sheet ---
def ensure_headers_exist(service, spreadsheet_id, sheet_name, headers):
    """Checks if headers exist in the first row, adds/updates them if not."""
    if not service: return False
    try:
        range_to_read = f"{sheet_name}!A1:{chr(ord('A') + len(headers) - 1)}1"
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_to_read).execute()
        values = result.get('values', [])
        if not values or values[0] != headers:
            print(f"Headers missing or incorrect in '{sheet_name}'. Writing headers..."); body = {'values': [headers]}
            update_result = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1", valueInputOption='USER_ENTERED', body=body).execute()
            print(f"Headers written successfully to '{sheet_name}'.")
        return True
    except HttpError as error:
        if error.resp.status == 400 and ('Unable to parse range' in str(error) or 'exceeds grid limits' in str(error)): # Handle empty sheet range error or range not found
            print(f"Sheet '{sheet_name}' appears empty or range invalid. Writing headers...")
            try:
                body = {'values': [headers]}; update_result = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1", valueInputOption='USER_ENTERED', body=body).execute()
                print(f"Headers written successfully to '{sheet_name}'."); return True
            except HttpError as inner_error: print(f"An error occurred writing headers to new sheet '{sheet_name}': {inner_error}"); return False
        else: print(f"An error occurred checking/writing headers for sheet '{sheet_name}': {error}"); return False
    except Exception as e: print(f"An unexpected error occurred during header check/write: {e}"); return False

# --- Helper Function: Append to Google Sheet (No check/create logic here) ---
def append_to_sheet(service, spreadsheet_id, sheet_name, values):
    """Appends a row of values to a Google Sheet. Assumes sheet exists."""
    if not service: print("Sheets service not available. Skipping append."); return False
    try:
        range_to_append = f"{sheet_name}"; body = {'values': [values]}
        result = service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=range_to_append, valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body).execute()
        return True
    except HttpError as error: print(f"An error occurred appending to Sheet ID '{spreadsheet_id}', Sheet '{sheet_name}': {error}"); return False
    except Exception as e: print(f"An unexpected error occurred during sheet append: {e}"); return False

# --- Function to Process a Single URL Job (Syntax Corrected) ---
def process_url(job_config, drive_service, sheets_service, target_spreadsheet_id):
    """Handles capturing, uploading, and logging for one URL configuration."""
    url = job_config.get("url"); folder_id = job_config.get("folder_id"); sheet_name = job_config.get("sheet_name")
    if not all([url, folder_id, sheet_name]): print(f"Skipping job due to invalid data: {job_config}"); return

    print(f"\n--- Processing Job for Sheet: '{sheet_name}' (URL: {url}) ---")
    print(f"Drive Folder ID: {folder_id}"); print(f"Target Sheet: '{sheet_name}' in SheetID '{target_spreadsheet_id}'")

    capture_timestamp = datetime.now(); timestamp_str = capture_timestamp.strftime(RUN_TIMESTAMP_FORMAT); file_timestamp = capture_timestamp.strftime("%Y%m%d_%H%M%S")

    try: # Filename Sanitization
        sanitized_sheet_name = re.sub(r'[<>:"/\\|?*]+', '', str(sheet_name)); sanitized_sheet_name = re.sub(r'\s+', '_', sanitized_sheet_name).strip('_')
        sanitized_sheet_name = sanitized_sheet_name if sanitized_sheet_name else 'capture'; sanitized_sheet_name = sanitized_sheet_name[:100]
    except Exception as sanitize_e: print(f"Warning: Could not sanitize sheet name '{sheet_name}': {sanitize_e}. Using 'capture'."); sanitized_sheet_name = 'capture'

    jpg_filename = f'{file_timestamp}_{sanitized_sheet_name}_screenshot.jpg'; html_filename = f'{file_timestamp}_{sanitized_sheet_name}_pagesource.html'

    script_dir = os.path.dirname(os.path.abspath(__file__)); local_save_full_dir = os.path.join(script_dir, LOCAL_SAVE_DIR)
    if not os.path.exists(local_save_full_dir):
        try: os.makedirs(local_save_full_dir)
        except OSError as dir_e: print(f"ERROR: Could not create local directory {local_save_full_dir}: {dir_e}. Skipping job."); return

    local_png_temp_path = os.path.join(local_save_full_dir, f'temp_{file_timestamp}_{sanitized_sheet_name}.png'); local_jpg_path = os.path.join(local_save_full_dir, jpg_filename); local_html_path = os.path.join(local_save_full_dir, html_filename)

    driver = None; screenshot_success = False; html_success = False
    try: # Main Selenium block
        print("Setting up WebDriver..."); options = ChromeOptions(); initial_width = 1366; initial_height = 1080
        options.add_argument("--headless=new"); options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage"); options.add_argument(f"--window-size={initial_width},{initial_height}")
        options.add_argument("--log-level=3"); options.add_argument("--hide-scrollbars"); options.add_argument("--disable-gpu")
        service = ChromeService(); driver = webdriver.Chrome(service=service, options=options); driver.set_page_load_timeout(60)

        print(f"Accessing URL: {url}"); driver.get(url)
        wait_time = 10; print(f"Waiting {wait_time}s for initial page load..."); time.sleep(wait_time)

        print("Attempting screenshot...")
        try: # Screenshot capture block
            js_commands = ["return document.body.parentNode.scrollHeight", "return document.documentElement.scrollHeight", "return document.body.scrollHeight", "return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight );"]
            total_height = 0
            for js in js_commands:
                try: height = driver.execute_script(js); total_height = max(total_height, int(height)) if isinstance(height, (int,float)) else total_height
                except Exception: pass
            max_screenshot_height = 30000; resize_height = min(total_height, max_screenshot_height) if total_height > initial_height else initial_height
            if resize_height > initial_height: print(f"Resizing window height to {resize_height}px..."); driver.set_window_size(initial_width, resize_height); time.sleep(2)
            else: print(f"Using initial window height ({initial_height}px)."); driver.set_window_size(initial_width, initial_height); time.sleep(0.5)

            driver.save_screenshot(local_png_temp_path); print(f"Temporary PNG saved: {local_png_temp_path}")
            print(f"Converting PNG to JPG: {local_jpg_path}...")
            with Image.open(local_png_temp_path) as img:
                 if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info): bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, mask=img.split()[-1]); img = bg
                 img.save(local_jpg_path, 'JPEG', quality=85)
            print("Conversion to JPG successful."); screenshot_success = True
            os.remove(local_png_temp_path); print(f"Removed temporary PNG.")
        except Exception as e:
            print(f"Error during screenshot capture/conversion: {e}")
            # --- SYNTAX FIX 1: Corrected temp file cleanup ---
            if os.path.exists(local_png_temp_path):
                try:
                    os.remove(local_png_temp_path)
                except Exception as remove_err:
                    print(f"Warning: Could not remove temp file {local_png_temp_path}: {remove_err}")
                    pass # Ignore cleanup error
            # --- End SYNTAX FIX 1 ---

        if screenshot_success: # HTML capture block
            print("Capturing HTML source...")
            try:
                html_content = driver.page_source
                with open(local_html_path, 'w', encoding='utf-8') as f: f.write(html_content)
                print(f"HTML source saved: {local_html_path}"); html_success = True
            except Exception as e: print(f"Error saving HTML source: {e}")
        else: print("Skipping HTML capture due to earlier screenshot failure.")

    except Exception as e: print(f"An error occurred during Selenium operation for {url}: {e}")
    finally: # Driver quit block
        # --- SYNTAX FIX 2: Corrected driver quit ---
        if driver:
            print("Closing WebDriver.")
            try:
                driver.quit()
            except Exception as qe:
                print(f"Warning: Error while closing WebDriver: {qe}")
        # --- End SYNTAX FIX 2 ---


    # --- Upload to Google Drive ---
    jpg_file_id = None; jpg_link = None; html_file_id = None; html_link = None
    if screenshot_success: jpg_file_id, jpg_link = upload_to_drive(drive_service, local_jpg_path, jpg_filename, folder_id, 'image/jpeg')
    if html_success: html_file_id, html_link = upload_to_drive(drive_service, local_html_path, html_filename, folder_id, 'text/html')

    # --- Ensure Target Sheet Exists and Has Headers ---
    sheet_ready = False; print(f"Ensuring target sheet '{sheet_name}' exists and has headers...")
    if ensure_sheet_exists(sheets_service, target_spreadsheet_id, sheet_name):
        if ensure_headers_exist(sheets_service, target_spreadsheet_id, sheet_name, EXPECTED_HEADERS): sheet_ready = True
        else: print(f"Failed to ensure headers in sheet '{sheet_name}'. Skipping append.")
    else: print(f"Failed to ensure sheet '{sheet_name}' exists. Skipping append.")

    # --- Log to Google Sheets ---
    if sheet_ready:
        image_link_for_sheet = jpg_link if jpg_link else "JPG Upload Failed" if screenshot_success else "Capture Failed"
        html_link_for_sheet = html_link if html_link else "HTML Upload Failed" if html_success else "Capture Skipped/Failed"
        sheet_values = [timestamp_str, image_link_for_sheet, html_link_for_sheet]
        print(f"Appending to Google Sheet '{sheet_name}': {sheet_values}")
        append_success = append_to_sheet(sheets_service, target_spreadsheet_id, sheet_name, sheet_values)
        if append_success: print("Append successful.")
    else: print("Skipping append operation due to sheet/header setup failure.")

    # --- Cleanup Local Files ---
    print("Cleaning up local files for this job..."); files_to_remove = [local_jpg_path, local_html_path, local_png_temp_path]
    for f_path in files_to_remove:
        if os.path.exists(f_path):
            try: os.remove(f_path)
            except Exception as e: print(f"Warning: Error removing local file {f_path}: {e}")
    print("Local files cleanup finished.")

    print(f"--- Finished Processing Job for Sheet: '{sheet_name}' ---")

# --- Main Execution Logic ---
def main():
    """Main function to run the scraper jobs."""
    start_time = time.time()
    print(f"Starting Web Capture and Upload Process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    script_dir = os.path.dirname(os.path.abspath(__file__)); local_save_full_dir = os.path.join(script_dir, LOCAL_SAVE_DIR)
    if not os.path.exists(local_save_full_dir):
        try: os.makedirs(local_save_full_dir); print(f"Created local directory: {local_save_full_dir}")
        except Exception as e: print(f"CRITICAL ERROR: Could not create local directory {local_save_full_dir}: {e}"); return

    print("\nAuthenticating with Google...")
    drive_service, sheets_service = get_authenticated_services()
    if not drive_service or not sheets_service: print("Failed to authenticate/build Google services. Exiting."); return

    print(f"\nFetching job configurations from Google Sheet '{CONFIG_SHEET_NAME}'...")
    scrape_jobs = get_jobs_from_sheet(sheets_service, CONFIG_SPREADSHEET_ID, CONFIG_SHEET_NAME)

    print("\nStarting processing of fetched jobs...")
    if not scrape_jobs: print("No valid jobs found in the config sheet. Exiting."); return

    job_count = len(scrape_jobs); print(f"Found {job_count} valid job(s).")
    for i, job in enumerate(scrape_jobs):
        print(f"\n>>> Starting Job {i+1} of {job_count} <<<")
        if isinstance(job, dict): process_url(job, drive_service, sheets_service, CONFIG_SPREADSHEET_ID)
        else: print(f"Skipping item {i+1}: Invalid job format (expected dictionary).")
        print(f">>> Finished Job {i+1} of {job_count} <<<")

    end_time = time.time(); duration = end_time - start_time
    print("\n--------------------------------------------------")
    print(f"All processed jobs finished in {duration:.2f} seconds.")
    print(f"Script finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
    print("--------------------------------------------------")

if __name__ == '__main__':
    if not os.path.exists(TOKEN_FILE) and os.path.exists(CREDENTIALS_FILE):
         print("\n" + "="*60); print("IMPORTANT: Google Authentication Required!"); print("Looks like this is the first run or scopes/token are missing."); print(f"Ensure '{CREDENTIALS_FILE}' is present."); print("A browser window will open shortly for you to authorize access"); print("to Google Drive and Google Sheets."); print("Make sure to grant permissions for BOTH services."); print("="*60 + "\n"); time.sleep(4)
    main()
