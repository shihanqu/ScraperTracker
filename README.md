# ScraperTracker
A webpage image and HTML archiver that works with google drive and google sheets.

Okay, here is a README file suitable for the script. You can save this content as `README.md` in the same directory as your Python script (`main.py`) and `credentials.json`.

```markdown
# Webpage Capture & Google Drive/Sheets Logger

This Python script automates the process of capturing website screenshots (as JPG images) and their HTML source code. It uploads these files to specified Google Drive folders and logs the capture details, including direct links to the uploaded files, into designated tabs within a central Google Sheet.

The script reads its job configurations directly from a 'CONFIG' tab within the specified Google Sheet, making it easy to manage multiple scraping tasks. It also automatically creates the target logging sheets (tabs) with appropriate headers if they don't already exist.

## Features

* Captures webpage screenshots and saves them as JPG files.
    * Attempts to capture the full scrollable page height (may vary based on website complexity).
* Saves the complete HTML source code of the webpage.
* Uploads the generated JPG and HTML files to specific Google Drive folders defined per job.
* Logs capture timestamp, Google Drive links for the image and HTML files to a Google Sheet.
* Reads job configurations (Target URL, Drive Folder ID, Target Sheet Name) from a `CONFIG` tab in a designated Google Sheet.
* Automatically creates the target Google Sheet tabs (if they don't exist) and adds headers (`Capture Date`, `Image URL`, `HTML Copy`).
* Uses Google OAuth 2.0 for secure authentication with Google Drive and Google Sheets APIs.
* Generates timestamped filenames prefixed with the date for easy sorting (e.g., `YYYYMMDD_HHMMSS_SheetName_screenshot.jpg`).

## Prerequisites

1.  **Python:** Python 3.7 or higher installed.
2.  **Pip:** Python package installer (usually comes with Python).
3.  **WebDriver:**
    * Google Chrome and [ChromeDriver](https://chromedriver.chromium.org/downloads) OR Mozilla Firefox and [GeckoDriver](https://github.com/mozilla/geckodriver/releases).
    * The WebDriver executable must be in your system's PATH or you will need to modify the script to provide the explicit path.
4.  **Google Account:** A standard Google account.
5.  **Google Cloud Platform Project:** A project set up in [Google Cloud Console](https://console.cloud.google.com/).

## Required Python Libraries

Install the necessary libraries using pip:

```bash
pip install selenium google-api-python-client google-auth-oauthlib google-auth-httplib2 Pillow
```

## Setup Instructions

### 1. Google Cloud API Credentials

1.  **Create/Select Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project or select an existing one.
2.  **Enable APIs:**
    * Navigate to "APIs & Services" > "Library".
    * Search for and enable the **Google Drive API**.
    * Search for and enable the **Google Sheets API**.
3.  **Create OAuth Credentials:**
    * Go to "APIs & Services" > "Credentials".
    * Click "+ CREATE CREDENTIALS" > "OAuth client ID".
    * If prompted, configure the "OAuth consent screen". Choose "External" user type for testing/personal use, provide an app name (e.g., "Web Scraper Logger"), your email address for user support and developer contact. Add your Google account email address as a Test User on the "Test users" step. Save and continue.
    * Select "Desktop app" as the Application type.
    * Give the client ID a name (e.g., "Web Scraper Desktop Client").
    * Click "Create".
4.  **Download Credentials:**
    * A pop-up will show your Client ID and Client Secret. Click the "DOWNLOAD JSON" button.
    * Rename the downloaded file to `credentials.json`.
    * Place this `credentials.json` file in the **same directory** as the Python script (`main.py`). **Keep this file secure!**

### 2. Google Sheet Setup

1.  **Create Spreadsheet:** Create a new Google Sheet or use an existing one. This sheet will hold both the configuration and the output logs.
2.  **Note Spreadsheet ID:** Open the spreadsheet. The URL will look like `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`. Copy the `SPREADSHEET_ID` part.
3.  **Set Fixed ID in Script:** Ensure the `CONFIG_SPREADSHEET_ID` variable near the top of the Python script (`main.py`) is set to this ID:
    ```python
    CONFIG_SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE'
    ```
4.  **Create `CONFIG` Tab:**
    * Create a new sheet/tab within your spreadsheet and name it **exactly** `CONFIG`.
    * Set up the following columns starting in cell `A1`:
        * `A1`: `url`
        * `B1`: `folder_id`
        * `C1`: `sheet_name`
    * Starting from row 2, list your scraping jobs:
        * **Column A (url):** The full URL of the webpage to capture.
        * **Column B (folder_id):** The ID of the Google Drive folder where files for this URL should be uploaded. (Get the ID from the folder's URL: `https://drive.google.com/drive/folders/FOLDER_ID`).
        * **Column C (sheet_name):** The exact name of the target sheet/tab within *this same spreadsheet* where the logs for this URL should be appended. The script will create this sheet if it doesn't exist.

### 3. Google Drive Folders

* Ensure that the Google Drive folders specified by the `folder_id` values in your `CONFIG` sheet exist.
* Verify that the Google account you will authenticate the script with has **Edit** or **Contributor** access to these folders.

## Running the Script

1.  **Navigate:** Open a terminal or command prompt and navigate to the directory containing `main.py` and `credentials.json`.
2.  **Execute:** Run the script using Python:
    ```bash
    python main.py
    ```
3.  **First-Run Authentication:**
    * The first time you run the script (or after deleting `token.json`), a message will appear indicating that authentication is required.
    * Your web browser should automatically open to a Google authentication page.
    * Log in with the Google account that has access to the configured Google Sheet and Drive folders.
    * Review the permissions requested (access to Drive files, access to Sheets) and click "Allow" or "Continue".
    * You might see a warning about the app not being verified by Google if you chose "External" user type during consent screen setup – proceed if you trust the script (click "Advanced" > "Go to [Your App Name] (unsafe)").
    * Once authorized, the browser might show a success message, and you can close it.
    * The script will create a `token.json` file in the same directory. This file stores your authorization tokens so you don't have to log in every time. **Do not share `token.json`.**
4.  **Subsequent Runs:** The script will use the `token.json` file to authenticate automatically.
5.  **Re-authentication:** If you change the `SCOPES` in the script, encounter persistent authentication errors, or revoke access via your Google Account settings, delete `token.json` and run the script again to re-authorize.

### Scheduling Daily Runs

The script runs once when executed. To run it automatically every day, use your operating system's task scheduler:

* **Linux/macOS:** Use `cron`. Edit your crontab (`crontab -e`) and add a line like:
    ```cron
    0 8 * * * /usr/bin/python3 /path/to/your/script/main.py >> /path/to/your/script/cron.log 2>&1
    ```
    (This example runs the script at 8:00 AM daily. Adjust the time and paths accordingly. Redirecting output `>> cron.log 2>&1` is recommended for logging.)
* **Windows:** Use Task Scheduler. Create a new task that triggers daily and runs the Python executable with the script path as an argument.

## Output

* **Google Drive:** For each processed job, a JPG screenshot and an HTML file will be uploaded to the corresponding Google Drive folder specified in the `CONFIG` sheet. Filenames will be in the format `YYYYMMDD_HHMMSS_SheetName_Type.ext`.
* **Google Sheets:** For each processed job, a new row will be appended to the target sheet (specified by `sheet_name` in the `CONFIG` sheet).
    * If the target sheet doesn't exist, it will be created automatically.
    * If the sheet is new or empty, headers (`Capture Date`, `Image URL`, `HTML Copy`) will be added to the first row.
    * The appended row will contain:
        * Column A: Timestamp of the capture (e.g., `2025-04-29 11:30:00`).
        * Column B: A clickable link to the uploaded JPG file in Google Drive (or an error status).
        * Column C: A clickable link to the uploaded HTML file in Google Drive (or an error status).

## Troubleshooting / Notes

* **Sheet Access Errors (404/403):** Double-check that the `CONFIG_SPREADSHEET_ID` is correct, the target `sheet_name` in the `CONFIG` tab exactly matches the actual tab name (case-sensitive), and the authenticated user has **Edit** permissions for the Google Sheet.
* **Drive Upload Errors (404/403):** Verify the `folder_id` in the `CONFIG` tab is correct and that the authenticated user has **Edit** or **Contributor** access to that Google Drive folder.
* **Full-Page Screenshots:** The script attempts to capture the full page height by resizing the browser window based on JavaScript calculations. This may not work perfectly on all websites, especially those with infinite scroll, dynamic content loading, or complex CSS layouts. The resulting screenshot might be cut off or have rendering issues on such pages. A maximum height limit is also imposed to prevent excessive memory usage.
* **Authentication:** Ensure `credentials.json` is present and valid. Delete `token.json` if you encounter persistent auth errors or change API scopes.
```
