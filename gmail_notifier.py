# C:\Users\pc\OneDrive\Desktop\phantom_alert_bot\gmail_notifier.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
import logging
import config # configモジュールをインポート

logger = logging.getLogger(__name__)

class GmailNotifier:
    def __init__(self): # <--- ここが引数なしになっていることを再度確認
        """
        GmailNotifier インスタンスを初期化する。
        送信者、パスワード、受信者の情報を config.py から読み込む。
        """
        # config.py から設定を読み込む
        self.sender_email = getattr(config, 'GMAIL_SENDER_EMAIL', None)
        self.sender_password = getattr(config, 'GMAIL_APP_PASSWORD', None) # GMAIL_APP_PASSWORDを使用
        self.recipient_emails = getattr(config, 'GMAIL_RECIPIENT_EMAILS', []) # リストを想定

        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587 # TLS

        # 通知が有効かどうかを判断
        self.is_enabled = bool(self.sender_email and self.sender_password and self.recipient_emails)

        if self.is_enabled:
            logger.info("GmailNotifier が有効です。")
        else:
            logger.warning("GmailNotifier は無効です。config.py に GMAIL_SENDER_EMAIL、GMAIL_APP_PASSWORD、または GMAIL_RECIPIENT_EMAILS が設定されていません。")

    def send_email_notification(self, subject: str, body: str, image_path: str = None) -> bool:
        """
        Gmail経由でメールを送信する。画像添付も可能。
        
        Args:
            subject (str): メールの件名。
            body (str): メールの本文。
            image_path (str, optional): 添付する画像のファイルパス。デフォルトは None。
        Returns:
            bool: 送信に成功した場合は True、失敗した場合は False。
        """
        if not self.is_enabled:
            logger.debug("GmailNotifier が無効なため、メール通知をスキップしました。")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(self.recipient_emails)
        msg['Subject'] = subject

        # メールの本文 (テキスト)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 画像添付
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as fp:
                    img = MIMEImage(fp.read())
                img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                msg.attach(img)
                logger.debug(f"画像ファイルをメールに追加しました: {image_path}")
            except Exception as e:
                logger.error(f"Gmailへの画像の読み込みまたは添付エラー: {e}", exc_info=True)
        elif image_path: # image_path が指定されているが存在しない場合
            logger.warning(f"Gmail用に指定された画像ファイルが見つかりません: {image_path}")

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls() # TLSで暗号化
                server.login(self.sender_email, self.sender_password)
                text = msg.as_string()
                server.sendmail(self.sender_email, self.recipient_emails, text) # recipient_emails は sendmail 用にリストであるべき
            logger.info(f"Gmail通知を送信しました。件名: '{subject}', 送信先: {', '.join(self.recipient_emails)}")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("Gmail認証に失敗しました。アプリパスワードとGmail設定が正しいか確認してください。", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Gmail通知の送信中にエラーが発生しました: {e}", exc_info=True)
            return False

# 使用例 (この部分は通常、ボットのメインロジックから呼び出される)
if __name__ == '__main__':
    # テスト用のダミーのconfig設定を定義 (実際のconfigモジュールはインポートされない)
    class MockConfig:
        GMAIL_SENDER_EMAIL = "your_test_sender@gmail.com"
        GMAIL_APP_PASSWORD = "your_test_app_password"
        GMAIL_RECIPIENT_EMAILS = ["your_test_recipient@example.com"]
        LOG_LEVEL = logging.DEBUG
        LOG_FILE = "test_gmail.log"
        LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # ロギングを設定 (テスト実行時のみ)
    logging.basicConfig(level=MockConfig.LOG_LEVEL, format=MockConfig.LOG_FORMAT)

    # configモジュールをモックに置き換え
    import sys
    sys.modules['config'] = MockConfig
    
    logger.info("\n--- gmail_notifier.py テスト開始 ---")

    # テストインスタンスを作成
    notifier = GmailNotifier() # 引数なしで初期化

    if notifier.is_enabled:
        test_subject = "テスト通知: Phantom Alert Bot"
        test_body = "これは Phantom Alert Bot からのテストメールです。\n正常に受信できましたか？"
        test_image_path = "test_chart.png" # 存在しないパスでもテスト

        # テスト用のダミー画像ファイルを生成
        from PIL import Image, ImageDraw, ImageFont
        try:
            img = Image.new('RGB', (200, 100), color = (73, 109, 137))
            d = ImageDraw.Draw(img)
            try:
                fnt = ImageFont.truetype("arial.ttf", 15)
            except IOError:
                fnt = ImageFont.load_default()
                logger.info("arial.ttf が見つかりませんでした。デフォルトフォントを使用します。")
            d.text((10,10), "テストチャート画像", font=fnt, fill=(255,255,0))
            img.save(test_image_path)
            logger.info(f"テスト画像 '{test_image_path}' を作成しました。")
        except ImportError:
            logger.warning("Pillow (PIL) がインストールされていません。テスト画像を作成できません。`pip install Pillow` でインストールしてください。")
            test_image_path = None # 画像添付なしでテスト

        # メール送信テスト
        logger.info(f"テストメールを {', '.join(notifier.recipient_emails)} に送信中...")
        success = notifier.send_email_notification(test_subject, test_body, image_path=test_image_path)
        if success:
            logger.info("テストメールを正常に送信しました。")
        else:
            logger.info("テストメールの送信に失敗しました。上記のログを確認してください。")

        # テスト画像を削除
        if test_image_path and os.path.exists(test_image_path):
            os.remove(test_image_path)
            logger.info(f"テスト画像 '{test_image_path}' を削除しました。")

    else:
        logger.warning("GmailNotifier が無効なため、テストをスキップします。config.py の設定を確認してください。")

    logger.info("\n--- gmail_notifier.py テスト終了 ---")
