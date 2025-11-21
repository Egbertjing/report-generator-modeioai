import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile
import time
import sys # Importing sys for potential use, though not strictly necessary here

# Load environment variables from .env file
load_dotenv() 

# Get system prompt and initialize constants
# Use .get() with a fallback to avoid KeyError if environment variables are missing
# Using sys.exit(1) is not ideal in a Gradio app, so we'll rely on the try-except blocks later.
system_prompt = os.environ.get('system_prompt', "你是一位专业的隐私和安全顾问，请根据用户提供的文件和查询生成一份详细的报告。")
api_key = os.environ.get('OPENAI_API_KEY')
base_url = os.environ.get('OPENAI_API_BASE')
model_name = os.environ.get('DEFAULT_MODEL', 'gpt-3.5-turbo')

# Initialize OpenAI client
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

# Function to generate content and prepare the downloadable file using streaming
def generate_report(message, file):
    """
    Generates the privacy report using streaming and prepares it as a downloadable file.
    
    This function is a generator that yields partial text results to the Textbox 
    while yielding None for the File component, and finally yields the complete 
    report and the file path.
    
    :param message: The user's text input.
    :param file: A list of uploaded file paths from gr.Files.
    :return: A generator yielding tuples of (report_text, file_path_for_download)
    """
    
    # 1. Read uploaded file content
    file_content = ""
    if file is not None:
        # file is typically a list of file paths from gr.Files
        for file_single in file:
            try:
                # Read file content and append to the message
                with open(file_single, "r", encoding="utf-8") as f:
                    file_content = f.read()
                message = message + "\n\n上传文件内容如下：\n" + file_content
            except Exception as e:
                # If file reading fails, yield the error and stop the generator
                yield f"读取文件失败: {e}", None
                return # Stop execution

    full_report = ""

    # 2. Call the Model (Streaming)
    try:
        # Set stream=True for streaming functionality
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            stream=True, 
        )

        # 3. Stream output and build full report
        for chunk in stream:
            # Check for content and append/yield
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                chunk_content = chunk.choices[0].delta.content
                full_report += chunk_content
                # Yield the current report text and None for the file path
                # This updates the report_output Textbox in real-time
                yield full_report, None

    except Exception as e:
        # If API call fails, yield the error message and stop
        yield f"报告生成失败，请检查API密钥或模型名称: {e}", None
        return # Stop execution

    # 4. Create a temporary file for download using the full_report
    # Only execute if streaming was successful and full_report is populated
    tmp_file_path = None
    if full_report:
        try:
            # Create a temporary file with a .txt extension. Gradio manages temp file cleanup.
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=f"_{int(time.time())}_report.txt", encoding="utf-8") as tmp_file:
                tmp_file.write(full_report)
                tmp_file_path = tmp_file.name
                
        except Exception as e:
            # Handle error during file writing by updating the report text
            full_report += f"\n\n[错误] 临时文件创建失败，无法下载: {e}"

    # 5. Yield the final result with the downloadable file path.
    # This final yield updates both the Textbox (last time) and the gr.File component.
    yield full_report, tmp_file_path

# Gradio Interface Definition
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("<div align='center'><h1>Modeio Bot - 隐私报告生成器</h1></div>")  # Centered Title
    gr.Markdown(
        """
        <details>
        <summary>示范 (Example)</summary>

        <pre>
        ## 例子：
        我们是一家在欧盟范围内运营的公司,我们在GDPR的管辖范畴内,请你审查一下这次传输是否存在安全漏洞和风险等级
        </pre>
        </details>
        """
    )
    
    # Input section
    with gr.Row():
        with gr.Column(scale=1):
            file_upload = gr.Files(label="上传文件 (.txt/.md) (Upload File)", file_types=[".txt", ".md"], height=173.59)
        with gr.Column(scale=2):
            # Input message box
            input_textbox = gr.Textbox(
                label="输入您的隐私审查请求 (Enter your privacy review request)",
                lines=5,
                autofocus=True
            )
            # Generation button
    generate_button = gr.Button("生成报告 (Generate Report)", variant="primary")

    # Output section
    report_output = gr.Textbox(
        label="生成的隐私报告 (Generated Privacy Report)",
        lines=15,
        autofocus=False,
        interactive=False
    )
    
    # Download section (The new feature: gr.File acts as a download link)
    download_file = gr.File(
        label="下载报告 (.txt) (Download Report)",
        file_types=[".txt"],
        height=100,
        type="filepath", # This is crucial: it tells Gradio to expect a local file path
        interactive=False # The user can't upload to this, only download from it
    )

    # Define the action when the button is clicked
    # The outputs are now mapped to report_output and download_file
    generate_button.click(
        fn=generate_report,
        inputs=[input_textbox, file_upload],
        outputs=[report_output, download_file],
        # api_name="generate_report_stream" # Optional: provides a streaming API endpoint
    )


# demo.launch(server_name="0.0.0.0",server_port=10000)
demo.launch()