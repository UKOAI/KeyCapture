# Building UKOAI Exam Monitor on Windows

## Prerequisites

1. **Install Python 3.9+** from https://www.python.org/downloads/
   - During installation, **tick "Add Python to PATH"** (this is critical)
   - Click "Install Now"

2. **Verify it worked** — open Command Prompt (Win+R, type `cmd`, Enter) and run:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x`.

## Build Steps

1. **SCP the Keylogger folder from the VM to your Windows machine.** From your Windows terminal:
   ```
   scp -r vm:/root/UKOAI/Keylogger C:\Users\James\Desktop\Keylogger
   ```

2. **Open Command Prompt** and navigate to the folder:
   ```
   cd C:\Users\James\Desktop\Keylogger
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Build the executable:**
   ```
   python build.py
   ```
   This takes a minute or two. Ignore any warnings.

5. **Your executable is at:**
   ```
   dist\UKOAI_Exam_Monitor.exe
   ```

That `.exe` is the single file you distribute. No Python needed to run it.

## Notes

- Windows SmartScreen may warn "Unknown publisher" when someone first runs it. Click "More info" then "Run anyway". This is normal for unsigned executables.
- To avoid the SmartScreen warning you'd need to code-sign the exe, which requires buying a certificate (~$200-400/year). Probably not worth it.
- The exe will be ~15-30MB (it bundles the entire Python runtime).
