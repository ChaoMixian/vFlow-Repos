#!/usr/bin/env python3
"""
vFlow工作流仓库索引生成器
自动扫描workflows目录并生成index.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def normalize_id(filename):
    """从文件名获取ID（去除.json扩展名）"""
    return filename.replace('.json', '') if filename.endswith('.json') else filename


def validate_workflow(data, filename):
    """
    验证工作流数据
    返回: (is_valid, error_message, cleaned_data)
    """
    # 检查是否有_meta
    if '_meta' not in data:
        return False, f"缺少 '_meta' 字段", None

    meta = data['_meta']

    # 验证_meta必需字段
    required_meta_fields = ['id', 'name', 'description', 'author', 'version', 'vFlowLevel']
    missing_fields = [field for field in required_meta_fields if field not in meta]

    if missing_fields:
        return False, f"_meta缺少必需字段: {', '.join(missing_fields)}", None

    # 验证_meta中的ID与文件名一致
    expected_id = normalize_id(filename)
    meta_id = meta['id']

    if meta_id != expected_id:
        return False, f"_meta.id 不匹配: 文件名='{expected_id}', _meta.id='{meta_id}'", None

    # 检查工作流是否有关键字段（可选，为了兼容性）
    # if 'id' not in data or 'steps' not in data:
    #     return False, "工作流缺少 'id' 或 'steps' 字段", None

    return True, None, data


def clean_workflow_for_repo(data):
    """
    清理工作流数据，准备发布到仓库
    - 将isEnabled、isFavorite、wasEnabledBeforePermissionsLost设置为false
    - 保留_meta信息
    """
    cleaned = data.copy()

    # 强制设置为false的字段
    cleaned['isEnabled'] = False
    cleaned['isFavorite'] = False
    cleaned['wasEnabledBeforePermissionsLost'] = False

    return cleaned


def scan_directory(directory_path):
    """
    扫描目录中的所有工作流JSON文件
    返回: (valid_items, errors, skipped_files)
    """
    items = []
    errors = []
    skipped_files = []

    dir_path = Path(directory_path)

    if not dir_path.exists():
        print(f"❌ 错误: 目录不存在: {directory_path}")
        return items, errors, skipped_files

    # 遍历目录中的所有JSON文件
    for filepath in dir_path.glob('*.json'):
        # 跳过index.json
        if filepath.name == 'index.json':
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 验证工作流
            is_valid, error_msg, _ = validate_workflow(data, filepath.name)

            if not is_valid:
                errors.append(f"❌ {filepath.name}: {error_msg}")
                skipped_files.append(filepath.name)
                continue

            # 提取元数据
            meta = data.get('_meta', {})

            # 清理工作流数据（保存到仓库的版本）
            cleaned_workflow = clean_workflow_for_repo(data)

            # 构建索引条目
            item = {
                'id': meta.get('id', normalize_id(filepath.name)),
                'name': meta.get('name', '未命名'),
                'description': meta.get('description', ''),
                'author': meta.get('author', '未知'),
                'version': meta.get('version', '1.0.0'),
                'vFlowLevel': meta.get('vFlowLevel', 1),
                'homepage': meta.get('homepage', ''),
                'tags': meta.get('tags', []),
                'updated_at': meta.get('updated_at', ''),
                'filename': filepath.name,
                # 构建下载URL
                'download_url': f"https://raw.githubusercontent.com/ChaoMixian/vFlow-Repos/main/workflows/{filepath.name}",
                # 本地文件路径（用于脚本更新文件）
                'local_path': str(filepath)
            }

            items.append(item)

            # 自动更新清理后的工作流文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cleaned_workflow, f, ensure_ascii=False, indent=2)

            print(f"✅ {filepath.name}: {item['name']} (v{item['version']}, Level {item['vFlowLevel']})")

        except json.JSONDecodeError as e:
            errors.append(f"❌ {filepath.name}: JSON解析错误 - {str(e)}")
            skipped_files.append(filepath.name)
        except Exception as e:
            errors.append(f"❌ {filepath.name}: {str(e)}")
            skipped_files.append(filepath.name)

    return items, errors, skipped_files


def generate_index(directory='workflows', output_file='index.json'):
    """生成索引文件"""
    print(f"🔍 扫描目录: {directory}")
    print("=" * 60)

    # 扫描工作流
    items, errors, skipped_files = scan_directory(directory)

    # 打印错误和跳过的文件
    if errors:
        print("\n❌ 验证失败:")
        for error in errors:
            print(f"  {error}")

    if skipped_files:
        print(f"\n⚠️  跳过 {len(skipped_files)} 个文件")

    # 按ID排序
    items.sort(key=lambda x: x['id'])

    # 构建索引
    index = {
        'version': '1.0',
        'last_updated': datetime.now().isoformat(),
        'total_count': len(items),
        'workflows': items
    }

    # 写入索引文件
    output_path = Path(directory) / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 成功索引 {len(items)} 个工作流")
    print(f"📝 索引文件: {output_path}")
    print(f"🕐 更新时间: {index['last_updated']}")

    # 如果有错误，返回非零退出码
    if errors:
        print(f"\n⚠️  存在 {len(errors)} 个错误，请检查！")
        sys.exit(1)


def main():
    """主函数"""
    # 默认扫描workflows目录
    workflows_dir = 'workflows'

    # 如果提供了命令行参数，使用指定的目录
    if len(sys.argv) > 1:
        workflows_dir = sys.argv[1]

    generate_index(workflows_dir)


if __name__ == '__main__':
    main()