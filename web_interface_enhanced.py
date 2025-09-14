"""
PCB训练系统增强版Web界面
包含模型管理和权重检查功能
"""

import json
import os
import shutil
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_file

from pcb_training_system import (
    get_all_tasks, get_queue_status, add_training_task,
    get_model_info, list_all_models, check_model_exists
)
from 训练目录监听 import organize_data

app = Flask(__name__)

THRESHOLD_FILE = Path(__file__).parent / 'thresholds.json'

def load_thresholds():
    if THRESHOLD_FILE.exists():
        with open(THRESHOLD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ok': 0.5, 'ng': 0.5}

def save_thresholds(data):
    with open(THRESHOLD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/tasks')
def api_tasks():
    """获取所有任务信息"""
    try:
        tasks = get_all_tasks()
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/queue_status')
def api_queue_status():
    """获取队列状态"""
    try:
        status = get_queue_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/models')
def api_models():
    """获取所有已训练的模型"""
    try:
        models = list_all_models()
        return jsonify({
            'success': True,
            'data': models
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/thresholds', methods=['GET', 'POST'])
def api_thresholds():
    try:
        if request.method == 'GET':
            return jsonify({'success': True, 'data': load_thresholds()})
        data = request.get_json() or {}
        save_thresholds({'ok': data.get('ok', 0.5), 'ng': data.get('ng', 0.5)})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/add_task', methods=['POST'])
def api_add_task():
    """手动触发训练"""
    try:
        data = request.get_json()
        name = data.get('name')
        source_dir = data.get('source_dir')
        if not name or not source_dir:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        base_dir = Path(__file__).parent
        dest_root = base_dir / 'data'
        data_root = dest_root / name
        if data_root.exists():
            shutil.rmtree(data_root)
        dest_root.mkdir(exist_ok=True)
        organize_data(source_dir, dest_root, name)
        task_id = add_training_task(name, str(data_root), 'yolov8', True)
        return jsonify({'success': True, 'data': {'task_id': task_id}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/check_model/<name>/<model_type>')
def api_check_model(name, model_type):
    """检查模型是否存在"""
    try:
        exists = check_model_exists(name, model_type)
        model_info = None
        if exists:
            model_info = get_model_info(name, model_type)

        return jsonify({
            'success': True,
            'data': {
                'exists': exists,
                'model_info': model_info
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download_trained_model/<name>/<model_type>')
def api_download_trained_model(name, model_type):
    """下载已训练的模型"""
    try:
        model_info = get_model_info(name, model_type)
        if not model_info or not model_info.get('model_path'):
            return jsonify({
                'success': False,
                'error': '模型文件不存在'
            }), 404

        model_path = Path(model_info['model_path'])
        if not model_path.exists():
            return jsonify({
                'success': False,
                'error': '模型文件不存在'
            }), 404

        return send_file(
            model_path,
            as_attachment=True,
            download_name=f"{name}_{model_type}_model.ckpt"
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # 创建模板目录
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    # 创建增强版HTML模板
    html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCB训练系统监控 - 增强版</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-running { color: #e67e22; font-weight: bold; }
        .status-completed { color: #27ae60; font-weight: bold; }
        .status-failed { color: #e74c3c; font-weight: bold; }
        .status-pending { color: #3498db; font-weight: bold; }
        .status-cancelled { color: #95a5a6; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .btn { padding: 8px 16px; margin: 4px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .btn:hover { opacity: 0.8; }
        .refresh-btn { position: fixed; top: 20px; right: 20px; z-index: 1000; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .checkbox-group { display: flex; align-items: center; }
        .checkbox-group input { width: auto; margin-right: 8px; }
        .model-exists { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .alert { padding: 15px; margin-bottom: 20px; border: 1px solid transparent; border-radius: 4px; }
        .alert-success { color: #155724; background-color: #d4edda; border-color: #c3e6cb; }
        .alert-danger { color: #721c24; background-color: #f8d7da; border-color: #f5c6cb; }
        .alert-warning { color: #856404; background-color: #fff3cd; border-color: #ffeaa7; }
        .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; }
        .tab.active { border-bottom-color: #3498db; background-color: #f8f9fa; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PCB缺陷检测训练系统 - 增强版</h1>
            <p>实时监控训练任务状态、模型管理和权重检查</p>
        </div>

        <button class="btn btn-primary refresh-btn" onclick="refreshAllData()">刷新数据</button>

        <div class="tabs">
            <div class="tab active" onclick="showTab('overview')">系统概览</div>
            <div class="tab" onclick="showTab('models')">模型管理</div>
            <div class="tab" onclick="showTab('tasks')">任务管理</div>
            <div class="tab" onclick="showTab('add-task')">添加任务</div>
        </div>

        <!-- 系统概览 -->
        <div id="overview" class="tab-content active">
            <div class="card">
                <h2>队列状态</h2>
                <div id="queue-status">加载中...</div>
            </div>

            <div class="card">
                <h2>最近任务</h2>
                <div id="recent-tasks">加载中...</div>
            </div>
        </div>

        <!-- 模型管理 -->
        <div id="models" class="tab-content">
            <div class="card">
                <h2>已训练模型</h2>
                <div id="models-table">加载中...</div>
            </div>
        </div>

        <!-- 任务管理 -->
        <div id="tasks" class="tab-content">
            <div class="card">
                <h2>所有训练任务</h2>
                <div id="all-tasks-table">加载中...</div>
            </div>
        </div>

        <!-- 添加任务 -->
        <div id="add-task" class="tab-content">
            <div class="card">
                <h2>阈值设置</h2>
                <div class="form-group">
                    <label>OK阈值:</label>
                    <input type="number" step="0.01" id="ok-threshold" required>
                </div>
                <div class="form-group">
                    <label>NG阈值:</label>
                    <input type="number" step="0.01" id="ng-threshold" required>
                </div>
                <button class="btn btn-primary" onclick="saveThresholds()">保存阈值</button>
                <hr>
                <h2>手动添加训练任务</h2>
                <form id="add-task-form">
                    <div class="form-group">
                        <label>任务名称 (产品号_元件名):</label>
                        <input type="text" id="task-name" placeholder="例如: 2150155000_PC1" required>
                    </div>
                    <div class="form-group">
                        <label>原始图片目录:</label>
                        <input type="text" id="source-dir" placeholder="例如: /path/to/output/2150155000_PC1" required>
                    </div>
                    <button type="submit" class="btn btn-success">添加任务</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        // 标签页切换
        function showTab(tabName) {
            // 隐藏所有标签页内容
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // 显示选中的标签页
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');

            // 根据标签页加载相应数据
            if (tabName === 'models') {
                loadModels();
            } else if (tabName === 'tasks') {
                loadAllTasks();
            } else if (tabName === 'overview') {
                loadQueueStatus();
                loadRecentTasks();
            }
        }

        function refreshAllData() {
            loadQueueStatus();
            loadRecentTasks();
            loadModels();
            loadAllTasks();
        }

        function loadQueueStatus() {
            fetch('/api/queue_status')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const status = data.data;
                        let html = `<p><strong>队列中任务数:</strong> ${status.queue_size}</p>`;

                        if (status.current_task) {
                            html += `<p><strong>当前执行任务:</strong> ${status.current_task.name} (${status.current_task.task_id})</p>`;
                        } else {
                            html += `<p><strong>当前状态:</strong> 无执行任务</p>`;
                        }

                        document.getElementById('queue-status').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function loadRecentTasks() {
            fetch('/api/tasks')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const tasks = data.data.slice(0, 5); // 只显示最近5个任务
                        let html = '<table><thead><tr><th>任务名称</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';

                        tasks.forEach(task => {
                            const statusClass = `status-${task.status}`;
                            const createdAt = new Date(task.created_at).toLocaleString();

                            html += `<tr>
                                <td>${task.name}</td>
                                <td class="${statusClass}">${task.status}</td>
                                <td>${createdAt}</td>
                                <td>
                                    <button class="btn btn-primary" onclick="viewTaskDetail('${task.task_id}')">详情</button>
                                </td>
                            </tr>`;
                        });

                        html += '</tbody></table>';
                        document.getElementById('recent-tasks').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function loadModels() {
            fetch('/api/models')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const models = data.data;
                        let html = '<table><thead><tr><th>产品名称</th><th>模型类型</th><th>创建时间</th><th>性能指标</th><th>操作</th></tr></thead><tbody>';

                        models.forEach(model => {
                            const createdAt = new Date(model.created_at).toLocaleString();

                            let metricsHtml = '暂无';
                            if (model.metrics) {
                                metricsHtml = Object.entries(model.metrics)
                                    .map(([key, value]) => `${key}: ${value.toFixed(4)}`)
                                    .join('<br>');
                            }

                            html += `<tr>
                                <td><strong>${model.name}</strong></td>
                                <td><span class="btn btn-info">${model.model_type}</span></td>
                                <td>${createdAt}</td>
                                <td>${metricsHtml}</td>
                                <td>
                                    <button class="btn btn-success" onclick="downloadTrainedModel('${model.name}', '${model.model_type}')">下载模型</button>
                                    <button class="btn btn-primary" onclick="viewModelDetail('${model.name}', '${model.model_type}')">详情</button>
                                </td>
                            </tr>`;
                        });

                        html += '</tbody></table>';
                        document.getElementById('models-table').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function loadAllTasks() {
            fetch('/api/tasks')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const tasks = data.data;
                        let html = '<table><thead><tr><th>任务ID</th><th>名称</th><th>状态</th><th>创建时间</th><th>指标</th><th>操作</th></tr></thead><tbody>';

                        tasks.forEach(task => {
                            const statusClass = `status-${task.status}`;
                            const createdAt = new Date(task.created_at).toLocaleString();

                            let metricsHtml = '暂无';
                            if (task.metrics) {
                                metricsHtml = Object.entries(task.metrics)
                                    .map(([key, value]) => `${key}: ${value.toFixed(4)}`)
                                    .join('<br>');
                            }

                            let actionsHtml = '';
                            if (task.status === 'pending') {
                                actionsHtml += `<button class="btn btn-danger" onclick="cancelTask('${task.task_id}')">取消</button>`;
                            }
                            if (task.status === 'completed' && task.model_path) {
                                actionsHtml += `<button class="btn btn-success" onclick="downloadModel('${task.task_id}')">下载模型</button>`;
                            }
                            actionsHtml += `<button class="btn btn-primary" onclick="viewLog('${task.task_id}')">查看日志</button>`;

                            html += `<tr>
                                <td>${task.task_id}</td>
                                <td>${task.name}</td>
                                <td class="${statusClass}">${task.status}</td>
                                <td>${createdAt}</td>
                                <td>${metricsHtml}</td>
                                <td>${actionsHtml}</td>
                            </tr>`;
                        });

                        html += '</tbody></table>';
                        document.getElementById('all-tasks-table').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function downloadTrainedModel(name, modelType) {
            window.open(`/api/download_trained_model/${name}/${modelType}`, '_blank');
        }

        function loadThresholds() {
            fetch('/api/thresholds')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('ok-threshold').value = data.data.ok;
                        document.getElementById('ng-threshold').value = data.data.ng;
                    }
                });
        }

        function saveThresholds() {
            const body = {
                ok: parseFloat(document.getElementById('ok-threshold').value),
                ng: parseFloat(document.getElementById('ng-threshold').value)
            };
            fetch('/api/thresholds', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    alert('阈值已保存');
                }
            });
        }

        document.getElementById('add-task-form').addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = {
                name: document.getElementById('task-name').value,
                source_dir: document.getElementById('source-dir').value
            };

            fetch('/api/add_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('任务添加成功: ' + data.data.task_id);
                    document.getElementById('add-task-form').reset();
                    refreshAllData();
                } else {
                    alert('添加失败: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('添加失败: ' + error.message);
            });
        });

        // 页面加载时获取数据
        loadThresholds();
        refreshAllData();

        // 每30秒自动刷新概览数据
        setInterval(() => {
            if (document.getElementById('overview').classList.contains('active')) {
                loadQueueStatus();
                loadRecentTasks();
            }
        }, 30000);
    </script>
</body>
</html>
    '''

    with open(templates_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

    print("PCB训练系统增强版Web界面启动")
    print("访问地址: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)

