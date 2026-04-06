from flask import Blueprint, render_template, jsonify, request
from extensions import db, socketio, CURRENT_USER_ID, CURRENT_USER_NAME
from config import Config
from models import GameRoom
from map_loader import MapLoader, MapData

CARD_CONFIG = Config.CARD_CONFIG

room_bp = Blueprint('room', __name__, url_prefix='/game/bo')

def get_current_user_id():
    return CURRENT_USER_ID

def get_current_user_name():
    return CURRENT_USER_NAME

@room_bp.route('/')
def index():
    return render_template('index.html')

@room_bp.route('/guide')
def game_guide():
    return render_template('game_guide.html')

@room_bp.route('/ai-room')
@room_bp.route('/ai-room/<int:room_id>')
def ai_room_view(room_id=None):
    player_id = get_current_user_id()
    map_name = request.args.get('map', 'default_map')
    
    if room_id:
        room = GameRoom.query.get(room_id)
        if not room:
            return "房间不存在", 404
        
        state = room.get_state()
        if 'terrain' not in state:
            map_data = MapLoader.load_map(map_name)
            state['terrain'] = map_data['terrain']
            state['terrain_types'] = map_data['terrain_types']
            state['piece_types'] = map_data['piece_types']
            room.set_state(state)
            db.session.commit()
        
        room_context = {
            'id': room.id,
            'player1_id': room.player1_id,
            'player2_id': room.player2_id if hasattr(room, 'player2_id') else -1
        }
        
        context = {
            'room': type('obj', (object,), room_context)(),
            'p1_name': '红方',
            'p2_name': 'AI',
            'user': '红方',
            'player_id': player_id,
            'map_name': map_name,
            'config': {
                'RED_PICTURE': Config.RED_PICTURE,
                'BLACK_PICTURE': Config.BLACK_PICTURE
            }
        }
    else:
        map_data = MapLoader.load_map(map_name)
        map_info = MapData(map_data)
        
        width = map_info.width
        height = map_info.height
        initial_board = []
        for _ in range(height): initial_board.append([None] * width)
        
        for piece in map_info.get_initial_pieces('R'):
            x, y = piece['x'], piece['y']
            if 0 <= y < height and 0 <= x < width:
                initial_board[y][x] = {'type': piece['type'], 'side': 'R'}
        
        for piece in map_info.get_initial_pieces('B'):
            x, y = piece['x'], piece['y']
            if 0 <= y < height and 0 <= x < width:
                initial_board[y][x] = {'type': piece['type'], 'side': 'B'}
        
        context = {
            'room': type('obj', (object,), {
                'id': 0,
                'player1_id': player_id,
                'player2_id': -1
            })(),
            'p1_name': '红方',
            'p2_name': 'AI',
            'user': '红方',
            'player_id': player_id,
            'map_name': map_name,
            'config': {
                'RED_PICTURE': Config.RED_PICTURE,
                'BLACK_PICTURE': Config.BLACK_PICTURE
            }
        }

    return render_template('ai_game.html', **context)

@room_bp.route('/api/create-ai', methods=['POST'])
def create_ai_room_api():
    data = request.json
    map_name = data.get('map_name', 'default_map')
    
    map_data = MapLoader.load_map(map_name)
    map_info = MapData(map_data)
    
    width = map_info.width
    height = map_info.height
    initial_board = []
    for _ in range(height): initial_board.append([None] * width)
    
    for piece in map_info.get_initial_pieces('R'):
        x, y = piece['x'], piece['y']
        if 0 <= y < height and 0 <= x < width:
            initial_board[y][x] = {'type': piece['type'], 'side': 'R'}
    
    for piece in map_info.get_initial_pieces('B'):
        x, y = piece['x'], piece['y']
        if 0 <= y < height and 0 <= x < width:
            initial_board[y][x] = {'type': piece['type'], 'side': 'B'}

    initial_cards = {}
    initial_cards[str(get_current_user_id())] = {k: v['limit'] for k, v in CARD_CONFIG.items()}

    game_state = {
        'board': initial_board,
        'turn': get_current_user_id(),
        'turn_number': 1,
        'steps_left': 0,
        'has_rolled': False,
        'winner': None,
        'cards': initial_cards,
        'active_card': None,
        'active_cards': {},
        'terrain': map_data['terrain'],
        'terrain_types': map_data['terrain_types'],
        'piece_types': map_data['piece_types']
    }

    new_room = GameRoom(player1_id=get_current_user_id(), status='waiting')
    new_room.set_state(game_state)
    db.session.add(new_room)
    db.session.commit()

    return jsonify({'success': True, 'room_id': new_room.id})

@room_bp.route('/api/get-maps')
def get_maps_api():
    try:
        maps = MapLoader.get_available_maps()
        map_list = []
        
        for map_name in maps:
            try:
                map_data = MapLoader.load_map(map_name)
                map_list.append({
                    'name': map_name,
                    'display_name': map_data['map_info']['name'],
                    'width': map_data['map_info']['width'],
                    'height': map_data['map_info']['height']
                })
            except Exception as e:
                pass
        
        return jsonify({'success': True, 'maps': map_list})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/map-editor')
def map_editor_view():
    return render_template('map_editor.html', user=CURRENT_USER_NAME)

@room_bp.route('/api/save-map', methods=['POST'])
def save_map_api():
    data = request.json
    map_name = data.get('map_name')
    map_data = data.get('map_data')
    
    if not map_name or not map_data:
        return jsonify({'success': False, 'msg': '缺少必要参数'})
    
    try:
        MapLoader.save_map(map_data, map_name, created_by=get_current_user_id())
        return jsonify({'success': True, 'msg': '地图保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'保存失败: {str(e)}'})

@room_bp.route('/api/load-map/<map_name>')
def load_map_api(map_name):
    try:
        map_data = MapLoader.load_map(map_name)
        return jsonify({'success': True, 'map_data': map_data})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/get-terrain-types')
def get_terrain_types_api():
    from models import Terrain
    
    try:
        terrains = Terrain.query.all()
        terrain_types = {}
        
        for terrain in terrains:
            terrain_types[terrain.terrain_id] = {
                'name': terrain.name,
                'description': terrain.description,
                'passability': terrain.passability,
                'move_cost': terrain.move_cost,
                'combat_bonus': terrain.combat_bonus,
                'color': terrain.color
            }
        
        return jsonify({'success': True, 'terrain_types': terrain_types})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/get-piece-types')
def get_piece_types_api():
    from models import Piece
    
    try:
        pieces = Piece.query.all()
        piece_types = {}
        
        for piece in pieces:
            piece_types[piece.piece_id] = {
                'name': piece.name,
                'description': piece.description,
                'move_range': piece.move_range,
                'combat_range': piece.combat_range,
                'base_power': piece.base_power,
                'attack_type': piece.attack_type,
                'move_cost': piece.move_cost,
                'defense_power': piece.defense_power,
                'attack_coop': piece.attack_coop,
                'defense_coop': piece.defense_coop,
                'coop_range': piece.coop_range,
                'piece_picture': piece.piece_picture,
                'terrain_change': piece.terrain_change
            }
        
        return jsonify({'success': True, 'piece_types': piece_types})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/update-terrain', methods=['POST'])
def update_terrain_api():
    from models import Terrain
    
    try:
        data = request.json
        terrain_id = data.get('terrain_id')
        terrain_data = data.get('terrain_data')
        
        if not terrain_id or not terrain_data:
            return jsonify({'success': False, 'msg': '缺少必要参数'})
        
        terrain = Terrain.query.filter_by(terrain_id=terrain_id).first()
        if not terrain:
            terrain = Terrain(terrain_id=terrain_id)
            db.session.add(terrain)
        
        for key, value in terrain_data.items():
            if hasattr(terrain, key):
                setattr(terrain, key, value)
        
        db.session.commit()
        return jsonify({'success': True, 'msg': '地形数据更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/delete-terrain', methods=['POST'])
def delete_terrain_api():
    from models import Terrain
    
    try:
        data = request.json
        terrain_id = data.get('terrain_id')
        
        if not terrain_id:
            return jsonify({'success': False, 'msg': '缺少必要参数'})
        
        terrain = Terrain.query.filter_by(terrain_id=terrain_id).first()
        if not terrain:
            return jsonify({'success': False, 'msg': '地形不存在'})
        
        if terrain_id == 'plain':
            return jsonify({'success': False, 'msg': '不能删除平原地形'})
        
        db.session.delete(terrain)
        db.session.commit()
        return jsonify({'success': True, 'msg': '地形数据删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/update-piece', methods=['POST'])
def update_piece_api():
    from models import Piece
    
    try:
        data = request.json
        piece_id = data.get('piece_id')
        piece_data = data.get('piece_data')
        
        if not piece_id or not piece_data:
            return jsonify({'success': False, 'msg': '缺少必要参数'})
        
        piece = Piece.query.filter_by(piece_id=piece_id).first()
        if not piece:
            piece = Piece(piece_id=piece_id)
            db.session.add(piece)
        
        for key, value in piece_data.items():
            if hasattr(piece, key):
                setattr(piece, key, value)
        
        db.session.commit()
        return jsonify({'success': True, 'msg': '棋子数据更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/delete-piece', methods=['POST'])
def delete_piece_api():
    from models import Piece
    
    try:
        data = request.json
        piece_id = data.get('piece_id')
        
        if not piece_id:
            return jsonify({'success': False, 'msg': '缺少必要参数'})
        
        piece = Piece.query.filter_by(piece_id=piece_id).first()
        if not piece:
            return jsonify({'success': False, 'msg': '棋子不存在'})
        
        if piece_id == 'X':
            return jsonify({'success': False, 'msg': '不能删除枭棋子'})
        
        db.session.delete(piece)
        db.session.commit()
        return jsonify({'success': True, 'msg': '棋子数据删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@room_bp.route('/api/ai-init')
def get_ai_init_state():
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({'success': False, 'msg': '缺少 room_id'})
    
    room = GameRoom.query.get(int(room_id))
    if not room:
        return jsonify({'success': False, 'msg': '房间不存在'})
    
    state = room.get_state()
    return jsonify({
        'success': True,
        'state': state,
        'room_id': room.id
    })
