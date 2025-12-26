"""
启动脚本
"""
from app import app
from config import Config

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          企业微信智能机器人 - AI Customer Service            ║
╠══════════════════════════════════════════════════════════════╣
║  回调地址: http://<your-domain>/wecom/callback               ║
║  健康检查: http://<your-domain>/health                       ║
║  服务端口: {Config.FLASK_PORT}                                          ║
║  AI模型:   {Config.AI_MODEL}                                     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

