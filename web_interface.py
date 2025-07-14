"""
PCB训练系统Web界面
提供训练状态监控和结果查看功能
"""

from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_file

from pcb_training_system import (
    get_all_tasks, get_queue_status, get_task_info, add_training_task,
    training_system, get_model_info, list_all_models, check_model_exists
)

app = Flask(__name__)


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


@app.route('/api/task/<task_id>')
def api_task_detail(task_id):
    """获取任务详细信息"""
    try:
        task_info = get_task_info(task_id)
        if task_info:
            return jsonify({
                'success': True,
                'data': task_info
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/add_task', methods=['POST'])
def api_add_task():
    """手动添加训练任务"""
    try:
        data = request.get_json()
        name = data.get('name')
        data_root = data.get('data_root')
        model_type = data.get('model_type', 'patchcore')
        force_retrain = data.get('force_retrain', False)

        if not name or not data_root:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400

        task_id = add_training_task(name, data_root, model_type, force_retrain)
        return jsonify({
            'success': True,
            'data': {'task_id': task_id}
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


@app.route('/api/model/<name>')
def api_model_info(name):
    """获取指定产品的模型信息"""
    try:
        model_type = request.args.get('model_type')
        model_info = get_model_info(name, model_type)

        if model_info:
            return jsonify({
                'success': True,
                'data': model_info
            })
        else:
            return jsonify({
                'success': False,
                'error': '模型不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/check_model/<name>/<model_type>')
def api_check_model(name, model_type):
    """检查模型是否存在"""
    try:
        exists = check_model_exists(name, model_type)
        return jsonify({
            'success': True,
            'data': {'exists': exists}
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


@app.route('/api/cancel_task/<task_id>', methods=['POST'])
def api_cancel_task(task_id):
    """取消任务"""
    try:
        success = training_system.cancel_task(task_id)
        return jsonify({
            'success': success,
            'message': '任务已取消' if success else '无法取消任务'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download_model/<task_id>')
def api_download_model(task_id):
    """下载训练好的模型"""
    try:
        task_info = get_task_info(task_id)
        if not task_info or not task_info.get('model_path'):
            return jsonify({
                'success': False,
                'error': '模型文件不存在'
            }), 404

        model_path = Path(task_info['model_path'])
        if not model_path.exists():
            return jsonify({
                'success': False,
                'error': '模型文件不存在'
            }), 404

        return send_file(
            model_path,
            as_attachment=True,
            download_name=f"{task_info['name']}_model.ckpt"
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/training_log/<task_id>')
def api_training_log(task_id):
    """获取训练日志"""
    try:
        task_info = get_task_info(task_id)
        if not task_info:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404

        log_file = Path(task_info['output_dir']) / 'training.log'
        if not log_file.exists():
            return jsonify({
                'success': True,
                'data': '暂无训练日志'
            })

        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()

        return jsonify({
            'success': True,
            'data': log_content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # 创建模板目录
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    # 创建简单的HTML模板
    html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCB训练系统监控</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-running { color: #e67e22; }
        .status-completed { color: #27ae60; }
        .status-failed { color: #e74c3c; }
        .status-pending { color: #3498db; }
        .status-cancelled { color: #95a5a6; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .btn { padding: 8px 16px; margin: 4px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .metric-item { background: #ecf0f1; padding: 10px; border-radius: 4px; }
        .refresh-btn { position: fixed; top: 20px; right: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PCB缺陷检测训练系统</h1>
            <p>实时监控训练任务状态和结果</p>
        </div>

        <button class="btn btn-primary refresh-btn" onclick="refreshData()">刷新数据</button>

        <div class="card">
            <h2>队列状态</h2>
            <div id="queue-status">加载中...</div>
        </div>

        <div class="card">
            <h2>训练任务</h2>
            <div id="tasks-table">加载中...</div>
        </div>

        <div class="card">
            <h2>手动添加任务</h2>
            <form id="add-task-form">
                <p>
                    <label>任务名称: </label>
                    <input type="text" id="task-name" placeholder="例如: 2150155000_PC1" required>
                </p>
                <p>
                    <label>数据目录: </label>
                    <input type="text" id="data-root" placeholder="例如: /path/to/data/2150155000_PC1" required>
                </p>
                <p>
                    <label>模型类型: </label>
                    <select id="model-type">
                        <option value="patchcore">PatchCore</option>
                        <option value="efficient_ad">EfficientAD</option>
                    </select>
                </p>
                <button type="submit" class="btn btn-success">添加任务</button>
            </form>
        </div>
    </div>

    <script>
        function refreshData() {
            loadQueueStatus();
            loadTasks();
        }

        function loadQueueStatus() {
            fetch('/api/queue_status')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const status = data.data;
                        let html = `<p>队列中任务数: ${status.queue_size}</p>`;

                        if (status.current_task) {
                            html += `<p>当前执行任务: <strong>${status.current_task.name}</strong> (${status.current_task.task_id})</p>`;
                        } else {
                            html += `<p>当前无执行任务</p>`;
                        }

                        document.getElementById('queue-status').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function loadTasks() {
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
                        document.getElementById('tasks-table').innerHTML = html;
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function cancelTask(taskId) {
            if (confirm('确定要取消这个任务吗？')) {
                fetch(`/api/cancel_task/${taskId}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        refreshData();
                    })
                    .catch(error => console.error('Error:', error));
            }
        }

        function downloadModel(taskId) {
            window.open(`/api/download_model/${taskId}`, '_blank');
        }

        function viewLog(taskId) {
            fetch(`/api/training_log/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const logWindow = window.open('', '_blank');
                        logWindow.document.write(`<pre>${data.data}</pre>`);
                    } else {
                        alert('无法获取日志: ' + data.error);
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        document.getElementById('add-task-form').addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = {
                name: document.getElementById('task-name').value,
                data_root: document.getElementById('data-root').value,
                model_type: document.getElementById('model-type').value
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
                    refreshData();
                } else {
                    alert('添加失败: ' + data.error);
                }
            })
            .catch(error => console.error('Error:', error));
        });

        // 页面加载时获取数据
        refreshData();

        // 每30秒自动刷新
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
    '''

    with open(templates_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

    print("PCB训练系统Web界面启动")
    print("访问地址: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

