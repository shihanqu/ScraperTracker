# TrackerScraper
A webpage image and HTML archiver that works with google drive and google sheets.

```markdown
# Tracker Scraper V1.1

## Description

`TrackerScraperV1.1.py` is a Python script designed to automate the process of monitoring web pages. It periodically captures screenshots (as JPG) and HTML source code of specified URLs, uploads these files to designated Google Drive folders, and logs the capture details (timestamp, Drive file links) into specific tabs within a Google Sheet.

Configuration for which URLs to track, where to save the files (Drive Folder IDs), and where to log results (target Sheet Name) is dynamically read from a central Google Sheet (`CONFIG` tab). The script also automatically creates the target logging sheets (tabs) with appropriate headers if they do not already exist.

## Features

* **Web Page Capture:** Takes full-page screenshots (attempted via JS resize) and saves as JPG. Captures complete HTML source code.
* **Google Drive Upload:** Uploads the captured JPG screenshot and HTML file to a specific Google Drive folder designated for each tracked URL.
* **Google Sheets Logging:** Appends a new row for each capture to a specific sheet (tab) within a master Google Sheet. The row includes the capture timestamp and direct links to the uploaded files on Google Drive.
* **Dynamic Configuration:** Reads job configurations (URL, Drive Folder ID, Target Sheet Name) from a `CONFIG` tab within a specified Google Sheet. No need to edit the script to add/remove jobs.
* **Automatic Sheet Creation:** Checks if the target logging sheet (tab) exists before appending. If not, it automatically creates the sheet and adds the required header row (`Capture Date`, `Image URL`, `HTML Copy`).
* **Date-Prefixed Filenames:** Uploaded filenames are prefixed with the capture timestamp (YYYYMMDD_HHMMSS) for easy sorting and uniqueness. Example: `20250429_113500_MySheetName_screenshot.jpg`.
* **Authentication Handling:** Uses OAuth 2.0 for secure Google API access, storing refresh tokens in `token.json` for subsequent runs.

## Prerequisites

1.  **Python:** Python 3.7 or higher recommended.
2.  **pip:** Python package installer (usually comes with Python).
3.  **Google Account:** A Google account with access to Google Drive and Google Sheets.
4.  **Google Cloud Project:**
    * Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
    * Enable the **Google Drive API** and **Google Sheets API** for this project.
    * Create **OAuth 2.0 Client IDs** credentials for a **Desktop application**.
    * Download the credentials JSON file and rename it to `credentials.json`.
5.  **WebDriver:**
    * Google Chrome browser installed.
    * [ChromeDriver](https://chromedriver.chromium.org/downloads) installed and accessible in your system's PATH, or its path specified within the script (currently assumes it's in PATH). Ensure the ChromeDriver version matches your Google Chrome browser version.
6.  **Git (Optional):** For cloning the repository if applicable.

## Installation & Setup

1.  **Get the Script:** Clone the repository or download `TrackerScraperV1.1.py`.
2.  **Place Credentials:** Put the downloaded `credentials.json` file in the same directory as the script.
3.  **Install Libraries:** Open your terminal or command prompt, navigate to the script's directory, and install the required Python packages:
    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib Pillow selenium requests
    ```
    *(Alternatively, if a `requirements.txt` file is provided: `pip install -r requirements.txt`)*
4.  **Set up Google Sheet:**
    * Create a new Google Sheet or use an existing one. Note its **Spreadsheet ID** (from the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`).
    * Make sure the `CONFIG_SPREADSHEET_ID` variable near the top of the `TrackerScraperV1.1.py` script is set to this correct ID.
    * Create a tab within this spreadsheet named exactly `CONFIG`.
    * Set up the `CONFIG` tab as described in the Configuration section below.

## Configuration (Google Sheet `CONFIG` Tab)

The script reads its job configurations from a tab named `CONFIG` within the Google Sheet specified by `CONFIG_SPREADSHEET_ID` in the script.

* **Location:** The data must start in cell `A1`.
* **Row 1:** Must contain the exact headers: `url`, `folder_id`, `sheet_name`.
* **Row 2 onwards:** Each row represents one scraping job.

**Columns:**

* **`url` (Column A):** The full URL of the web page to capture.
* **`folder_id` (Column B):** The Google Drive Folder ID where the screenshot and HTML file for this URL should be uploaded. You can find this ID in the URL when viewing the folder on Google Drive (`https://drive.google.com/drive/folders/FOLDER_ID`). Ensure the authenticated user has **Edit** access to this folder.
* **`sheet_name` (Column C):** The exact name of the target sheet (tab) within the *same spreadsheet* where the log entry (Timestamp, Image Link, HTML Link) for this URL should be appended. If a sheet with this name doesn't exist, the script will create it and add headers.

**Example `CONFIG` Tab Structure:**

| url                                             | folder_id                         | sheet_name              |
| :---------------------------------------------- | :-------------------------------- | :---------------------- |
| `https://www.amazon.com/s?k=magnetic+balls`     | `1kTfMRoGjvBHsIaasdfCtJBr0g6e0Ws` | `Amazon-magnetic-balls` |
| `https://www.amazon.com/s?k=magneballs`         | `1kTfMRoGjvBHsIaasdfCtJBr0g6e0Ws` | `Amazon-magneballs`     |
| `https://www.ebay.com/sch/i.html?_nkw=magnetic` | `1ABCDefGjBHsIaJJ4SJzhCtJBr0gZwd` | `Ebay-magnetic-general` |
| `https://www.mysite.com/product`                | `1ABCDefGjBHsIaJJ4SJzhCtJBr0gZwd` | `MySite-ProductPage`    |
| ...                                             | ...                               | ...                     |

*(Ensure the values in your sheet match your actual URLs, Folder IDs, and desired Sheet Names exactly)*

## Usage

1.  Navigate to the script's directory in your terminal.
2.  Run the script using Python:
    ```bash
    python TrackerScraperV1.1.py
    ```
3.  **First Run Authentication:** The first time you run the script (or after deleting `token.json`), it will:
    * Print instructions to the console.
    * Open a web browser window, prompting you to log in to your Google Account.
    * Ask you to grant permission for the script to access Google Drive and Google Sheets.
    * **Important:** Ensure you authenticate with the Google Account that has the necessary permissions for the specified Drive folders and the configuration/target Google Sheet.
    * After successful authentication, it will create a `token.json` file in the script's directory. This file stores the authorization token so you don't have to re-authenticate every time. **Keep `token.json` secure!**
4.  **Subsequent Runs:** The script will use the `token.json` file to authenticate automatically. It will:
    * Read jobs from the `CONFIG` sheet.
    * Process each job:
        * Capture screenshot/HTML.
        * Upload files to the specified Drive folder.
        * Ensure the target sheet exists and has headers.
        * Append the log entry to the target sheet.
    * Print progress and status messages to the console.

## Scheduling with Cron (Daily Execution)

To run the script automatically (e.g., daily), you can use `cron`, a time-based job scheduler available on Unix-like operating systems (Linux, macOS).

**1. What is Cron?**
Cron allows you to schedule commands or scripts to run periodically at specific times and dates.

**2. Editing the Crontab:**
You edit your user's cron schedule (crontab) using the command:
```bash
crontab -e
```
This will open your crontab file in your default text editor (like `nano` or `vim`).

**3. Cron Job Format:**
Each line in the crontab represents a job and follows this format:
```
# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday; 7 is also Sunday on some systems)
# │ │ │ │ │
# │ │ │ │ │
# * * * * * /path/to/command/to/execute
```
An asterisk (`*`) means "every". For example, `0 3 * * *` means "at 3:00 AM every day".

**4. Important Considerations for Cron Jobs:**

* **Absolute Paths:** Cron jobs often run with a minimal environment and may not know the `PATH` to your Python interpreter or the script. Always use **absolute paths**. Find your Python interpreter's path (`which python` or `which python3`) and the full path to your script.
* **Working Directory:** Cron jobs usually start in the user's home directory. Your script likely depends on finding `credentials.json` and `token.json` in its *own* directory, and it creates `temp_web_captures` there too. The safest way to handle this is to `cd` into the script's directory before running it.
* **Logging Output:** Cron jobs run in the background. To see output or errors, redirect standard output (`stdout`) and standard error (`stderr`) to a log file. `> /path/to/logfile.log 2>&1` appends both stdout and stderr to the specified file.
* **Virtual Environments:** If you installed the Python libraries in a virtual environment (recommended), you MUST use the path to the Python interpreter *inside* that environment (e.g., `/path/to/project/.venv/bin/python`).

**5. Example Cron Job (Daily at 3:00 AM):**

Let's assume:
* Your script is located at `/home/user/projects/TrackerScraper/TrackerScraperV1.1.py`.
* Your Python 3 interpreter (possibly in a virtualenv) is at `/home/user/projects/TrackerScraper/.venv/bin/python`.
* You want to log output to `/home/user/projects/TrackerScraper/scraper.log`.

Add the following line to your crontab using `crontab -e`:

```crontab
0 3 * * * cd /home/user/projects/TrackerScraper && /home/user/projects/TrackerScraper/.venv/bin/python /home/user/projects/TrackerScraper/TrackerScraperV1.1.py > /home/user/projects/TrackerScraper/scraper.log 2>&1
```

**Explanation of the example:**

* `0 3 * * *`: Run at 3:00 AM every day.
* `cd /home/user/projects/TrackerScraper`: **Change directory** to where the script and credential files are located.
* `&&`: Run the next command only if the `cd` was successful.
* `/home/user/projects/TrackerScraper/.venv/bin/python`: Execute using the Python interpreter **from the virtual environment** (adjust path if not using venv or if it's elsewhere).
* `/home/user/projects/TrackerScraper/TrackerScraperV1.1.py`: The absolute path to the script.
* `> /home/user/projects/TrackerScraper/scraper.log 2>&1`: Redirect standard output and standard error to the log file. Check this file if the script doesn't seem to run correctly via cron.

Save the crontab file after adding the line. Cron will automatically pick up the schedule.

## Troubleshooting

* **Authentication Errors (`token.json` issues):** Delete `token.json` and re-run the script manually to re-authenticate. Ensure you grant permissions for both Drive and Sheets.
* **`credentials.json` not found:** Make sure the file is named exactly `credentials.json` and is in the same directory as the script.
* **Sheet/Folder Not Found (404 Errors):** Double-check the `SPREADSHEET_ID`, `CONFIG_SHEET_NAME`, `folder_id` values, and target `sheet_name` values for typos. Ensure they exist and the authenticated user has the correct permissions (View for config sheet, Edit for target sheets and Drive folders).
* **Permission Denied (403 Errors):** Verify the authenticated Google account has necessary permissions (View/Edit) for the specified Google Sheet and Drive Folders.
* **Cron Job Not Running:** Check the cron log file specified in your cron command for errors. Verify absolute paths and directory changes (`cd`). Ensure the cron daemon is running (`sudo systemctl status cron` or similar). Check system mail (`mail` command) for cron errors if logging wasn't set up.
* **Selenium/WebDriver Errors:** Ensure ChromeDriver is installed, its version matches Chrome, and it's in the system PATH or configured correctly. Headless mode can sometimes behave differently; test manually without headless if needed. Some websites might block automated access.


```
