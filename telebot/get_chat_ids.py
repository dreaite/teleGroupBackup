#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取群组ID的辅助脚本
"""

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
try:
    from telethon.tl.functions.messages import GetForumTopicsRequest
except ImportError:
    from telethon.tl.functions.channels import GetForumTopicsRequest
import os
import asyncio
import yaml

async def main():
    # Load config locally relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'group_backup_config.yml')

    if not os.path.exists(config_path):
        print(f"❌ 错误: 找不到配置文件 {config_path}")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 错误: 读取配置文件失败: {e}")
        return

    telegram_config = config.get('telegram', {})
    api_id = telegram_config.get('api_id')
    api_hash = telegram_config.get('api_hash')
    
    if not api_id or not api_hash:
        print("❌ 错误: not set api_id or api_hash in config yml")
        return
    
    # Use 'group_backup' session to share login with the main bot
    # The session file is located in /data/bot/group_backup/group_backup.session
    original_session_path = '/data/bot/group_backup/group_backup.session'
    
    if not os.path.exists(original_session_path):
         print(f"❌ 错误: 找不到会话文件 {original_session_path}")
         return

    # Copy session to a temp file to avoid "database is locked" error if bot is running
    import shutil
    import time
    
    temp_session_name = f'temp_session_{int(time.time())}'
    temp_session_path = f'{temp_session_name}.session'
    
    try:
        shutil.copy2(original_session_path, temp_session_path)
        print(f"已创建临时会话文件: {temp_session_path}")
    except Exception as e:
        print(f"❌ 错误: 复制会话文件失败: {e}")
        return

    # Create client using the temp session
    client = TelegramClient(temp_session_name, api_id, api_hash)
    
    try:
        print("正在连接到 Telegram...")
        try:
            await client.connect()
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return
        
        if not await client.is_user_authorized():
            print(f"❌ 错误: 会话 '{original_session_path}' 未登录")
            print("请先运行主程序完成登录")
            await client.disconnect()
            return
        
        # 获取当前用户信息
        me = await client.get_me()
        print(f"\n✅ 已登录: {me.first_name} (@{me.username})")
        print("=" * 80)
        
        print("\n📋 你的对话列表:\n")
        print(f"{'类型':<10} {'名称':<30} {'ID':<15} {'备注'}")
        print("-" * 80)
        
        dialog_count = 0
        async for dialog in client.iter_dialogs():
            # Determine detailed type and status
            type_str = "其他"
            status_note = ""
            
            if dialog.is_user:
                type_str = "私聊"
            elif dialog.is_group:
                if isinstance(dialog.entity, Chat):
                    type_str = "普通群组"
                    if getattr(dialog.entity, 'migrated_to', None):
                        status_note = "[已升级为超级群组]"
                    elif getattr(dialog.entity, 'deactivated', False):
                        status_note = "[已停用]"
                elif isinstance(dialog.entity, Channel):
                    type_str = "超级群组"
                    if getattr(dialog.entity, 'forum', False):
                        type_str = "论坛群组"
            elif dialog.is_channel:
                type_str = "频道"
                
            # Filter: Show groups, channels
            if dialog.is_group or dialog.is_channel:
                # Handle potentially long names
                display_name = dialog.name
                if display_name and len(display_name) > 30:
                    display_name = display_name[:28] + ".."
                elif not display_name:
                    display_name = "<Unknown>"

                print(f"{type_str:<10} {display_name:<30} {dialog.id:<15} {status_note}")
                dialog_count += 1
                
                if dialog.is_group and getattr(dialog.entity, 'forum', False):
                    try:
                        # Fetch topics using raw request
                        request = GetForumTopicsRequest(
                            channel=dialog.entity,
                            offset_date=None,
                            offset_id=0,
                            offset_topic=0,
                            limit=20,
                            q='' # Required argument for some versions
                        )
                        result = await client(request)
                        
                        topics = getattr(result, 'topics', [])
                        if not topics and isinstance(result, list):
                            topics = result
                            
                        if topics:
                            for topic in topics:
                                t_name = topic.title
                                if len(t_name) > 25:
                                    t_name = t_name[:22] + ".."
                                print(f"   ╰─ [话题] {t_name:<25} ID: {topic.id}")
                        else:
                             print(f"   ╰─ (无话题)")
                             
                    except Exception as e:
                         # Attempt without 'q' argument if first try failed (older/newer schema differences)
                         try:
                             request = GetForumTopicsRequest(
                                channel=dialog.entity,
                                offset_date=None,
                                offset_id=0,
                                offset_topic=0,
                                limit=20
                            )
                             result = await client(request)
                             topics = getattr(result, 'topics', [])
                             if topics:
                                for topic in topics:
                                    t_name = topic.title
                                    if len(t_name) > 25:
                                        t_name = t_name[:22] + ".."
                                    print(f"   ╰─ [话题] {t_name:<25} ID: {topic.id}")
                         except Exception as e2:
                             # print(f"   ╰─ 获取话题失败: {e2}")
                             pass

        print("-" * 80)
        print(f"\n共找到 {dialog_count} 个群组/频道")
        
        print("\n💡 提示:")
        print("1. 复制你想要的群组ID")
        print("2. 在 group_backup_config.yml 文件中配置 groups")
        print("3. 群组ID已经是负数格式,可以直接使用")
        
    finally:
        if client.is_connected():
            await client.disconnect()
        # Cleanup temp session file
        if os.path.exists(temp_session_path):
            try:
                os.remove(temp_session_path)
                print(f"\n🗑️  已清理临时会话文件")
            except Exception as e:
                print(f"Note: Failed to delete temp session: {e}")

if __name__ == '__main__':
    asyncio.run(main())
