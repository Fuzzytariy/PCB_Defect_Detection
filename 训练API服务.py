#!/usr/bin/env python3
"""
训练API服务
基于Flask的Web API，提供训练任务管理的HTTP接口
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# 导入训练任务管理器
from 训练任务管理器 import (
    task_manager, 
    add_training_task, 
    get_task_status, 
    get_queue_status,
    TaskStatus
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
app.config['JSON_AS_ASCII'] = False  # 支持中文JSON响应


def validate_training_config(config):
    """验证训练配置参数"""
    errors = []
    
    # 必需参数
    required_fields = ['name', 'root']
    for field in required_fields:
        if field not in config or not config[field]:
            errors.append(f"缺少必需参数: {field}")
    
    # 验证数据目录
    if 'root' in config and config['root']:
        data_path = config['root']
        if not os.path.exists(data_path):
            errors.append(f"数据目录不存在: {data_path}")
        else:
            # 检查子目录结构
            required_dirs = ['train/OK', 'test/OK', 'test/NG']
            for dir_path in required_dirs:
                full_path = os.path.join(data_path, dir_path)
                if not os.path.exists(full_path):
                    errors.append(f"缺少必需目录: {dir_path}")
    
    # 验证骨干网络
    valid_backbones = ['resnet18', 'resnet34', 'resnet50', 'wide_resnet50_2']
    if 'backbone' in config and config['backbone'] not in valid_backbones:
        errors.append(f"无效的骨干网络: {config['backbone']}, 支持的选项: {valid_backbones}")
    
    # 验证数值参数
    if 'coreset_sampling_ratio' in config:
        ratio = config['coreset_sampling_ratio']
        if not isinstance(ratio, (int, float)) or ratio <= 0 or ratio > 1:
            errors.append("coreset_sampling_ratio 必须是 0-1 之间的数值")
    
    if 'num_neighbors' in config:
        neighbors = config['num_neighbors']
        if not isinstance(neighbors, int) or neighbors <= 0:
            errors.append("num_neighbors 必须是正整数")
    
    # 验证特征层
    if 'layers' in config:
        layers = config['layers']
        if not isinstance(layers, list) or not layers:
            errors.append("layers 必须是非空列表")
        else:
            valid_layers = ['layer1', 'layer2', 'layer3', 'layer4']
            for layer in layers:
                if layer not in valid_layers:
                    errors.append(f"无效的特征层: {layer}, 支持的选项: {valid_layers}")
    
    return errors


@app.route('/')
def index():
    """主页 - 显示API文档"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>训练任务管理API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            .delete { background: #f93e3e; }
            code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
            pre { background: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🚀 训练任务管理API</h1>
        <p>基于Flask的训练任务管理Web API服务</p>
        
        <h2>📋 API接口列表</h2>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/train</h3>
            <p><strong>功能:</strong> 添加训练任务</p>
            <p><strong>请求体:</strong></p>
            <pre>{
  "name": "任务名称",
  "root": "/path/to/data",
  "backbone": "resnet18",
  "layers": ["layer1", "layer2", "layer3"],
  "coreset_sampling_ratio": 0.1,
  "num_neighbors": 9
}</pre>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/queue</h3>
            <p><strong>功能:</strong> 获取队列状态</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/tasks</h3>
            <p><strong>功能:</strong> 获取所有任务列表</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/task/&lt;task_id&gt;</h3>
            <p><strong>功能:</strong> 获取特定任务详情</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method delete">DELETE</span> /api/task/&lt;task_id&gt;</h3>
            <p><strong>功能:</strong> 取消等待中的任务</p>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/health</h3>
            <p><strong>功能:</strong> 健康检查</p>
        </div>
        
        <h2>📊 当前状态</h2>
        <div id="status">加载中...</div>
        
        <script>
            // 获取当前状态
            fetch('/api/queue')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    statusDiv.innerHTML = `
                        <p><strong>队列大小:</strong> ${data.queue_size}</p>
                        <p><strong>当前任务:</strong> ${data.current_task ? data.current_task.name : '无'}</p>
                    `;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = '<p style="color: red;">获取状态失败</p>';
                });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': '训练任务管理API',
        'version': '1.0.0'
    })


@app.route('/api/train', methods=['POST'])
def create_training_task():
    """创建训练任务"""
    try:
        # 获取请求数据
        if not request.is_json:
            raise BadRequest("请求必须是JSON格式")
        
        config = request.get_json()
        if not config:
            raise BadRequest("请求体不能为空")
        
        # 验证配置
        errors = validate_training_config(config)
        if errors:
            return jsonify({
                'success': False,
                'error': '配置验证失败',
                'details': errors
            }), 400
        
        # 设置默认值
        training_config = {
            'name': config['name'],
            'root': os.path.abspath(config['root']),
            'backbone': config.get('backbone', 'resnet18'),
            'layers': config.get('layers', ['layer1', 'layer2', 'layer3']),
            'coreset_sampling_ratio': config.get('coreset_sampling_ratio', 0.1),
            'num_neighbors': config.get('num_neighbors', 9)
        }
        
        # 添加训练任务
        task_id = add_training_task(**training_config)
        
        # 获取队列状态
        queue_status = get_queue_status()
        
        logger.info(f"通过API添加训练任务: {task_id} - {training_config['name']}")
        
        return jsonify({
            'success': True,
            'message': '训练任务已添加成功',
            'task_id': task_id,
            'task_name': training_config['name'],
            'queue_status': {
                'queue_size': queue_status['queue_size'],
                'current_task': queue_status['current_task']['name'] if queue_status['current_task'] else None
            }
        })
        
    except BadRequest as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"创建训练任务失败: {e}")
        return jsonify({
            'success': False,
            'error': '内部服务器错误',
            'details': str(e)
        }), 500


@app.route('/api/queue', methods=['GET'])
def get_queue_info():
    """获取队列状态"""
    try:
        queue_status = get_queue_status()
        return jsonify({
            'success': True,
            'data': queue_status
        })
    except Exception as e:
        logger.error(f"获取队列状态失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取队列状态失败',
            'details': str(e)
        }), 500


@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有任务列表"""
    try:
        # 按状态分组
        tasks_by_status = {
            'running': [],
            'pending': [],
            'completed': [],
            'failed': [],
            'cancelled': []
        }
        
        for task_id, task in task_manager.tasks.items():
            task_info = {
                'task_id': task.task_id,
                'name': task.name,
                'root': task.root,
                'backbone': task.backbone,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message
            }
            
            status_key = task.status.value
            if status_key in tasks_by_status:
                tasks_by_status[status_key].append(task_info)
        
        # 按创建时间排序
        for status_tasks in tasks_by_status.values():
            status_tasks.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'tasks_by_status': tasks_by_status,
                'total_count': len(task_manager.tasks)
            }
        })
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取任务列表失败',
            'details': str(e)
        }), 500


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    """获取特定任务详情"""
    try:
        task_info = task_manager.get_task_info(task_id)
        
        if not task_info:
            return jsonify({
                'success': False,
                'error': f'任务不存在: {task_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': task_info
        })
        
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取任务详情失败',
            'details': str(e)
        }), 500


@app.route('/api/task/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """取消任务"""
    try:
        success = task_manager.cancel_task(task_id)
        
        if success:
            logger.info(f"通过API取消任务: {task_id}")
            return jsonify({
                'success': True,
                'message': f'任务 {task_id} 已取消'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'无法取消任务 {task_id}，可能任务不存在或已在执行中'
            }), 400
            
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return jsonify({
            'success': False,
            'error': '取消任务失败',
            'details': str(e)
        }), 500


@app.route('/api/config/template', methods=['GET'])
def get_config_template():
    """获取配置模板"""
    template = {
        "name": "示例训练任务",
        "root": "/path/to/your/data",
        "backbone": "resnet18",
        "layers": ["layer1", "layer2", "layer3"],
        "coreset_sampling_ratio": 0.1,
        "num_neighbors": 9
    }
    
    return jsonify({
        'success': True,
        'data': {
            'template': template,
            'options': {
                'backbones': ['resnet18', 'resnet34', 'resnet50', 'wide_resnet50_2'],
                'layers': ['layer1', 'layer2', 'layer3', 'layer4'],
                'coreset_sampling_ratio_range': [0.01, 1.0],
                'num_neighbors_range': [1, 50]
            }
        }
    })


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        stats = {
            'total_tasks': len(task_manager.tasks),
            'by_status': {},
            'recent_tasks': []
        }
        
        # 按状态统计
        for task in task_manager.tasks.values():
            status = task.status.value
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        # 最近的任务
        recent_tasks = sorted(
            task_manager.tasks.values(),
            key=lambda x: x.created_at,
            reverse=True
        )[:10]
        
        for task in recent_tasks:
            stats['recent_tasks'].append({
                'task_id': task.task_id,
                'name': task.name,
                'status': task.status.value,
                'created_at': task.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取统计信息失败',
            'details': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'success': False,
        'error': '接口不存在',
        'message': '请检查URL路径是否正确'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        'success': False,
        'error': '内部服务器错误',
        'message': '请联系管理员'
    }), 500


def main():
    """启动Flask应用"""
    import argparse
    
    parser = argparse.ArgumentParser(description="训练任务管理API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    logger.info(f"启动训练任务管理API服务...")
    logger.info(f"服务地址: http://{args.host}:{args.port}")
    logger.info(f"API文档: http://{args.host}:{args.port}")
    
    # 启动Flask应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True  # 支持多线程
    )


if __name__ == "__main__":
    main()