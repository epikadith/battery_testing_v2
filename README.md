# Android Battery Analysis with GenAI

This project provides a complete toolkit for collecting, analyzing, and reporting on Android battery consumption. It uses ADB to collect detailed `batterystats` from a device, processes and visualizes the data in a Jupyter Notebook, and leverages the Google Gemini API to generate an expert-level analysis with actionable recommendations.

This is designed to help users identify which applications and system processes are draining their battery and understand how to fix it.

## Features

- **Automated Log Collection:** Includes batch scripts to easily collect detailed battery and device information.
- **In-depth Parsing:** A Python module that parses complex `batterystats` dumps, including power consumption (mAh) and wakelock durations.
- **Data Visualization:** The Jupyter Notebook provides clear charts for battery level over time, top power-consuming apps, and longest-held wakelocks.
- **AI-Powered Reporting:** Uses the Google Gemini API to analyze the processed data and generate a detailed report that explains the causes of battery drain and suggests concrete solutions.
- **PDF Report Generation:** A script to generate a clean, timestamped PDF report of the entire analysis, perfect for sharing.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.8+**
2.  **Android Debug Bridge (ADB):** This must be installed and accessible from your system's PATH. You can download it as part of the [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools).

## Setup & Installation

Follow these steps to get the project running.

1.  **Clone or Download the Project**

    If you are using git, clone the repository. Otherwise, download the project files as a ZIP.

2.  **Create a Virtual Environment (Recommended)**

    It is highly recommended to use a virtual environment to keep project dependencies isolated. Open your terminal in the project directory and run:

    ```bash
    # Create the virtual environment folder
    python -m venv .venv

    # Activate the environment (for Windows)
    .\.venv\Scripts\activate
    ```

3.  **Install Dependencies**

    With your virtual environment active, install all the necessary Python libraries from the `requirements.txt` file:

    ```bash
    pip install -r requirements.txt
    ```

## How to Use

### Step 1: Connect Your Android Device

1.  **Enable Developer Options:** On your Android phone (instructions are general but confirmed for OnePlus devices), go to **Settings > About Phone** and tap on **"Build number"** 7 times. This will unlock the "Developer options" menu.
2.  **Enable USB Debugging:** Go to **Settings > System > Developer options** and toggle on **USB debugging**.
3.  **Connect to PC:** Connect your phone to your computer via a USB cable. You may see a prompt on your phone asking you to **"Allow USB debugging"**. Check the box to always allow and tap **OK**.

### Step 2: Collect Battery Logs

For the most accurate analysis, it's best to first reset the stats, use your phone normally, and then collect the logs.

1.  **Reset Stats (Optional):** To start with a clean slate, run the `reset_logs.bat` script. This will clear the existing battery statistics on your device. After running it, disconnect your phone and use it for a few hours to generate meaningful data.
2.  **Collect Logs:** After you have used your phone for a while, reconnect it and run the `collect_logs.bat` script. This will:
    - Create a new timestamped folder inside the `logs` directory.
    - Save the `batterystats.txt`, `battery.txt`, and `device_info.txt` files into that new folder.

### Step 3: Run the Analysis Notebook

1.  **Launch Jupyter:** In your terminal (with the virtual environment still active), start the Jupyter Notebook server:
    ```bash
    jupyter notebook
    ```
2.  **Open the Notebook:** Your web browser will open the Jupyter interface. Click on `results.ipynb` to open it.
3.  **Run the Cells:** Run the notebook cells sequentially from top to bottom. This will load, parse, and visualize your collected log data.

### Step 4: Generate the AI-Powered Report

The final part of the notebook uses the Google Gemini API to analyze your data.

1.  **Get a Gemini API Key:** If you don't have one, get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  **Set the API Key:** In the notebook, you will find a cell designed for setting your API key. Run this cell and enter your key when prompted. Using the `getpass` method is recommended for security, as it won't display your key in the notebook.
3.  **Run the Final Cell:** Execute the last cell to send your data to the Gemini API. It will print a detailed report analyzing the top battery offenders and providing actionable recommendations.

### Step 5: Generate a PDF Report (Optional)

If you want a shareable PDF summary of the analysis without running the Jupyter Notebook manually, you can use the `generate_report.py` script.

In your terminal (with the virtual environment active), simply run:
```bash
python generate_report.py
```
This will create a `results` directory (if it doesn't exist) and save a timestamped PDF file inside it.

## File Overview

-   `collect_logs.bat`: A script to collect battery statistics and device info from a connected Android device.
-   `reset_logs.bat`: A utility script to reset the battery statistics on the device for a clean analysis.
-   `parsing.py`: A Python module containing all the functions for parsing the raw log files.
-   `generate_report.py`: A script to automatically run the entire analysis and generate a timestamped PDF report.
-   `results.ipynb`: The main Jupyter Notebook for data processing, visualization, and generating the final AI report.
-   `requirements.txt`: A list of all Python dependencies required for the project.

