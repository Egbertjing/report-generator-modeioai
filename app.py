import gradio as gr
from openai import OpenAI
import os
import gradio as gr
import os
from dotenv import load_dotenv

load_dotenv() 


system_prompt = os.environ['system_prompt']

client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
    base_url=os.environ['OPENAI_API_BASE'],
)

def response(message, history, file=None):
    file_content = ""
    if file is not None:
        for file_single in file:
            with open(file_single, "r", encoding="utf-8") as f:
                file_content = f.read()
            message = message + "\n\n上传文件内容如下：\n" + file_content

    stream_response = client.chat.completions.create(
        model=os.environ['DEFAULT_MODEL'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        stream=True,
    )
    response = ''
    for chunk in stream_response:
        if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
            # if '<think>' in chunk.choices[0].delta.content:
            #     chunk.choices[0].delta.content = chunk.choices[0].delta.content.replace('<think>', '思维链')
            response += chunk.choices[0].delta.content
            yield response

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("<div align='center'><h1>Modeio Bot</h1></div>")  # 居中显示Title
    gr.Markdown(
        """
        <details>
        <summary>示范</summary>

        <pre>
        ## 例子：
        我们是一家在欧盟范围内运营的公司，我们在GDPR的管辖范畴内，请你审查一下这次传输是否存在安全漏洞和风险等级：
        </pre>
        </details>
        """
    )
    file_upload = gr.Files(label="上传文件", file_types=[".txt", ".md"], height=150)
    chatbot = gr.ChatInterface(
        fn=response,
        type="messages",
        additional_inputs=[file_upload]
    )




demo.launch()

