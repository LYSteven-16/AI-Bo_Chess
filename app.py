from flask import Flask
from config import Config
from extensions import db, socketio
from models import User
from map_loader import MapLoader
import json
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    # 部署到服务器用，Socket.IO 路径需要与前端配置一致
    socketio.init_app(app, async_mode='eventlet', path='/game/bo/socket.io', cors_allowed_origins="*")

    # 注册蓝图
    from routes.room import room_bp
    # game.py 没有蓝图，它通过 socketio 事件工作，但需要被导入以注册事件
    import routes.game 

    app.register_blueprint(room_bp)

    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 创建默认匿名用户（如果不存在）
        default_user = db.session.get(User, 1)
        if not default_user:
            default_user = User(
                id=1,
                username='游客',
                email='anonymous@mubo.local'
            )
            db.session.add(default_user)
            db.session.commit()
        
        # 初始化地图数据到数据库（如果数据库中没有地图）
        from models import Map
        if Map.query.count() == 0:
            maps_dir = os.path.join(os.path.dirname(__file__), 'maps')
            if os.path.exists(maps_dir):
                for file_name in os.listdir(maps_dir):
                    if file_name.endswith('.json'):
                        map_name = file_name[:-5]
                        map_path = os.path.join(maps_dir, file_name)
                        try:
                            with open(map_path, 'r', encoding='utf-8') as f:
                                map_data = json.load(f)
                            MapLoader.import_map_from_file(map_name, map_data)
                            print(f"✓ 已导入地图: {map_name}")
                        except Exception as e:
                            print(f"导入地图 {map_name} 失败: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, port=5212, debug=True)