@echo off

:: Change the current working directory to the project folder
:: The /d switch ensures the drive letter changes correctly if needed
cd /d "C:\Users\#########################"

:: Set the OpenAI API Key as an environment variable for this session
set OPENAI_API_KEY=sk-proj-#####################

:: Execute the Python script and pass any command-line arguments (%*)
python main.py %*

:: Check the exit code (%errorlevel%)
:: If it is not equal to 0, an error occurred, so we pause to read the output
if %errorlevel% neq 0 (
    echo.
    echo An error occurred.
    pause
)