import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config.from_pyfile('config.py')

# 确保数据目录存在
os.makedirs(app.config['DATA_DIR'], exist_ok=True)

def get_selections():
    """获取已选择的图片数据"""
    selections_file = os.path.join(app.config['DATA_DIR'], 'selections.json')
    if os.path.exists(selections_file):
        with open(selections_file, 'r') as f:
            return json.load(f)
    return {}

def save_selections(selections):
    """保存选择的图片数据"""
    selections_file = os.path.join(app.config['DATA_DIR'], 'selections.json')
    with open(selections_file, 'w') as f:
        json.dump(selections, f, ensure_ascii=False, indent=4)

def get_categories():
    """获取一级文件夹列表"""
    categories = []
    if os.path.exists(app.config['IMG_DIR']):
        for name in os.listdir(app.config['IMG_DIR']):
            path = os.path.join(app.config['IMG_DIR'], name)
            if os.path.isdir(path):
                categories.append(name)
    return sorted(categories)

def get_category_images(category):
    """获取指定分类下的所有profile_geo图片"""
    images = []
    category_path = os.path.join(app.config['IMG_DIR'], category)
    
    if not os.path.exists(category_path):
        return images
    
    for item in os.listdir(category_path):
        item_path = os.path.join(category_path, item)
        if os.path.isdir(item_path):
            profile_geo = os.path.join(item_path, 'profile_geo.png')
            if os.path.exists(profile_geo):
                # 有图片
                rel_path = os.path.relpath(profile_geo, app.config['IMG_DIR'])
                images.append({
                    'folder': item,
                    'image_path': rel_path,
                    'has_image': True
                })
            '''
            else:
                # 没有图片
                images.append({
                    'folder': item,
                    'image_path': None,
                    'has_image': False
                })
            '''
    
    return images

@app.route('/')
def index():
    """首页 - 显示所有一级文件夹"""
    categories = get_categories()
    selections = get_selections()
    
    # 分页
    page = request.args.get('page', type=int)
    if page is None:
        page = session.get('last_page', 1)
    per_page = 10
    total = len(categories)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    session['last_page'] = page
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_categories = categories[start:end]
    
    return render_template('index.html', 
                          categories=paginated_categories,
                          selections=selections,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages)

@app.route('/category/<category>')
def category_view(category):
    """显示指定分类下的图片"""
    images = get_category_images(category)
    selections = get_selections()
    selected = selections.get(category, '')
    
    # 将选中的图片移到最前面，其余按文件夹名排序
    if selected:
        selected_item = next((item for item in images if item['image_path'] == selected), None)
        if selected_item:
            images.remove(selected_item)
            images.sort(key=lambda x: int(x['folder'].split('.')[0])) 
            images.insert(0, selected_item) 
    else:
        images.sort(key=lambda x: int(x['folder'].split('.')[0])) 
    
    return render_template('category.html', 
                          category=category,
                          images=images,
                          selected=selected)

@app.route('/select', methods=['POST'])
def select_image():
    """处理图片选择"""
    category = request.form.get('category')
    image_path = request.form.get('image_path')
    
    selections = get_selections()
    selections[category] = image_path
    save_selections(selections)
    
    return redirect(url_for('category_view', category=category))

@app.route('/unselect', methods=['POST'])
def unselect_image():
    """处理取消选择"""
    category = request.form.get('category')
    
    selections = get_selections()
    if category in selections:
        del selections[category]
        save_selections(selections)
    
    return redirect(url_for('category_view', category=category))

@app.route('/export-excel')
def export_excel():
    """导出选择结果到Excel"""
    selections = get_selections()
    data = []
    for category, image_path in selections.items():
        with open(os.path.join(app.config['IMG_DIR'], image_path).replace('.png', '.txt'), 'r') as f_r:
            profile_geo = f_r.read().strip()
        data.append({
            '名称': category,
            '搜索结果': image_path.split('/')[1].split('.')[1],
            'profile_geo': profile_geo
        })
    df_res = pd.DataFrame(data)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = f'selections_{timestamp}.xlsx'
    excel_path = os.path.join(app.config['DATA_DIR'], excel_filename)
    df_res.to_excel(excel_path, index=False)
    
    # 返回到页面
    categories = get_categories()
    page = request.args.get('page', type=int)
    if page is None:
        page = session.get('last_page', 1)
    per_page = 10
    total = len(categories)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    session['last_page'] = page

    start = (page - 1) * per_page
    end = start + per_page
    paginated_categories = categories[start:end]

    return render_template('index.html', 
                          categories=paginated_categories,
                          selections=selections,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages)

@app.route('/img/<path:filename>')
def serve_image(filename):
    """提供图片访问"""
    return send_from_directory(app.config['IMG_DIR'], filename)

if __name__ == '__main__':
    app.run(debug=True)