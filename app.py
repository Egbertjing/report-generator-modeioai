import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile
import time
import sys 

# Load environment variables from .env file
# load_dotenv() 

# Get system prompt and initialize constants
system_prompt = os.environ.get('system_prompt')
api_key = os.environ.get('OPENAI_API_KEY')
base_url = os.environ.get('OPENAI_API_BASE')
model_name = os.environ.get('DEFAULT_MODEL')

# Initialize OpenAI client
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)


def generate_report(message, file, regulations): 
    

    regulations_str = ""
    if regulations:
        # 将选中的法规列表转换为逗号分隔的字符串
        regulations_str = ", ".join(regulations)
        # 将法规要求添加到用户消息中
        message = f"请严格参照以下法规进行审查: **{regulations_str}**。\n\n" + message
        # print(message)
        
    full_report = f"--- 审查法规: {regulations_str if regulations_str else '未选择'} ---\n\n" # 报告开头增加法规信息
    
    # 2. Read uploaded file content
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

    # 3. Call the Model (Streaming)
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

        # 4. Stream output and build full report
        for chunk in stream:
            # Check for content and append/yield
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                chunk_content = chunk.choices[0].delta.content
                full_report += chunk_content
                # Yield the current report text and None for the file path
                yield full_report, None

    except Exception as e:
        # If API call fails, yield the error message and stop
        yield f"报告生成失败，请检查API密钥或模型名称: {e}", None
        return # Stop execution

    # 5. Create a temporary file for download using the full_report
    tmp_file_path = None
    if full_report:
        try:
            # Create a temporary file with a .txt extension.
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=f"_{int(time.time())}_report.txt", encoding="utf-8") as tmp_file:
                tmp_file.write(full_report)
                tmp_file_path = tmp_file.name
                
        except Exception as e:
            # Handle error during file writing
            full_report += f"\n\n[错误] 临时文件创建失败，无法下载: {e}"

    # 6. Yield the final result with the downloadable file path.
    yield full_report, tmp_file_path

# Gradio Interface Definition
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("<div align='center'><h1>Modeio Bot - 隐私报告生成器</h1></div>")
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
            # ！！！新增 Checklist ！！！
            regulation_checklist = gr.CheckboxGroup(
                label="选择适用的法规 (Select Applicable Regulations)",
                choices=["GDPR", "AIACT", "HIPAA"],
                value=["GDPR"] # 默认选中 GDPR 作为示例
            )
            file_upload = gr.Files(label="上传文件 (.txt/.md) (Upload File)", file_types=[".txt", ".md"], height=125)
            
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
    
    # Download section
    download_file = gr.File(
        label="下载报告 (.txt) (Download Report)",
        file_types=[".txt"],
        height=100,
        type="filepath",
        interactive=False
    )

    # Define the action when the button is clicked
    # ！！！修改 inputs 以包含 regulation_checklist ！！！
    generate_button.click(
        fn=generate_report,
        inputs=[input_textbox, file_upload, regulation_checklist],
        outputs=[report_output, download_file],
    )

demo.launch(server_name="0.0.0.0",server_port=10000)