# imgur_uploader.py
import requests
import logging
import os

logger = logging.getLogger(__name__)

class ImgurUploader:
    def __init__(self, client_id):
        self.client_id = client_id
        self.upload_url = "https://api.imgur.com/3/image"
        self.headers = {
            "Authorization": f"Client-ID {self.client_id}"
        }
        
        if not client_id:
            logger.warning("Imgur CLIENT_ID が設定されていません。ImgurUploaderは無効です。")
            self.is_enabled = False
        else:
            self.is_enabled = True
            logger.info("ImgurUploaderが有効です。")

    def upload_image(self, image_path, title=None, description=None):
        if not self.is_enabled:
            logger.warning("ImgurUploaderが無効なため、画像をアップロードしません。")
            return None
        
        if not os.path.exists(image_path):
            logger.error(f"指定された画像ファイルが見つかりません: {image_path}")
            return None

        with open(image_path, 'rb') as img_file:
            files = {'image': img_file.read()}
            data = {'title': title, 'description': description}

            try:
                response = requests.post(self.upload_url, headers=self.headers, files=files, data=data)
                response.raise_for_status() # HTTPエラーがあれば例外を発生させる
                result = response.json()
                if result['success']:
                    return result['data']['link']
                else:
                    logger.error(f"Imgur画像アップロードAPIエラー: {result.get('data', {}).get('error', '不明なエラー')}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Imgur画像アップロードのリクエストエラー: {e}")
                return None
            except Exception as e:
                logger.error(f"予期せぬエラーでImgur画像アップロードに失敗しました: {e}")
                return None

if __name__ == '__main__':
    # テスト実行
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- ImgurUploaderのテスト ---")

    # config.py から IMGUR_CLIENT_ID を直接読み込む
    # テスト時もconfigから読み込むか、環境変数で設定する方が良い
    from config import IMGUR_CLIENT_ID as TEST_IMGUR_CLIENT_ID # configからインポート

    if not TEST_IMGUR_CLIENT_ID:
        print("IMGUR_CLIENT_ID が config.py に設定されていません。テストスキップ。")
    else:
        uploader = ImgurUploader(TEST_IMGUR_CLIENT_ID)

        # テスト用のダミー画像ファイルを作成 (実際は既存の画像ファイルを使用)
        dummy_image_path = "test_image.png"
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 50), color = 'red')
            img.save(dummy_image_path)
            print(f"ダミー画像ファイルを作成しました: {dummy_image_path}")

            print("画像をImgurにアップロード中...")
            uploaded_url = uploader.upload_image(dummy_image_path, title="Test Upload from Python", description="This is a test image.")
            if uploaded_url:
                print(f"画像アップロード成功: {uploaded_url}")
            else:
                print("画像アップロード失敗。ログを確認してください。")

        except ImportError:
            print("Pillow (PIL) がインストールされていません。`pip install Pillow` を実行してください。")
            print("ダミー画像作成をスキップします。")
        except Exception as e:
            print(f"Imgurアップロードテスト中にエラーが発生しました: {e}")
        finally:
            if os.path.exists(dummy_image_path):
                os.remove(dummy_image_path)
                print(f"ダミー画像ファイル '{dummy_image_path}' を削除しました。")