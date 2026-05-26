import logging
import json
from pathlib import Path
from datetime import datetime

from telebot.ai_sdk import get_ai_provider

TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_SAFE_MESSAGE_LIMIT = 3800

class GroupSummarizer:
    def __init__(self, client, config, mapper, logger=None):
        self.client = client
        self.config = config
        self.mapper = mapper
        self.logger = logger or logging.getLogger(__name__)
        
        self.summary_config = config.get('summary', {})
        self.enabled = self.summary_config.get('enabled', False)
        self.provider = get_ai_provider(self.summary_config) if self.enabled else None
        if self.enabled and not self.provider:
            provider_name = self.summary_config.get('provider', 'openai')
            self.logger.error(f"Summary is enabled but AI provider is unavailable: {provider_name}")
        
        # State tracking for processed files
        self.data_dir = Path(config.get('settings', {}).get('backup_schedule', {}).get('local_export_dir', './data/exports'))
        self.summary_dir = self.data_dir / "summaries"
        self.state_file = self.data_dir / "summary_state.json"
        self.processed_files = self._load_state()
        self.focus_users = self._parse_focus_users()

    def _parse_focus_users(self):
        raw = self.config.get('settings', {}).get('focus_users', [])
        focused = set()
        for u in raw:
            if isinstance(u, int):
                focused.add(u)
        return focused

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return set(json.load(f))
            except:
                pass
        return set()

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(list(self.processed_files), f)
        except Exception as e:
            self.logger.error(f"Failed to save summary state: {e}")

    async def run_process(self, file_path: Path, target_id: int):
        """Process a single backup file for summary."""
        if not self.enabled or not self.provider:
            return

        file_key = file_path.name
        if file_key in self.processed_files:
            return

        self.logger.info(f"Generating summary for {file_key}...")
        
        messages = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"Failed to read backup file {file_path}: {e}")
            return

        if not messages:
            return

        # Group by Source
        source_groups = {} # source_id -> [msgs]
        
        for msg in messages:
            t_msg_id = msg.get('id')
            source_info = self.mapper.get_source_info(target_id, t_msg_id)
            
            source_id = None
            if source_info:
                source_id = source_info.get('source_chat_id')
                msg['_source_msg_id'] = source_info.get('source_msg_id')
            
            if not source_id:
                continue

            if source_id not in source_groups:
                source_groups[source_id] = []
            source_groups[source_id].append(msg)

        if not source_groups:
            self.logger.warning(f"No mapped source messages found for summary file {file_key}")
            self.processed_files.add(file_key)
            self._save_state()
            return

        # Process each Source
        all_sent = True
        for source_id, msgs in source_groups.items():
            if not await self._summarize_source(source_id, msgs, file_key):
                all_sent = False

        # Mark as done only after all summaries were sent successfully.
        if all_sent:
            self.processed_files.add(file_key)
            self._save_state()
        else:
            self.logger.warning(f"Summary file {file_key} was not marked processed because sending failed")

    async def _summarize_source(self, source_id, msgs, file_key):
        # Find Source Config
        source_conf = self.config.get('groups', {}).get(source_id)
        if not source_conf:
            source_conf = self.config.get('groups', {}).get(str(source_id), {})
        
        # Prepare Focus Users (Global + Source)
        current_focus_set = self.focus_users.copy()
        source_focus = source_conf.get('focus_users', [])
        for u in source_focus:
            if isinstance(u, int):
                current_focus_set.add(u)
        
        # Determine Summary Target
        summary_target_id = source_conf.get('summary_target')
        
        if not summary_target_id:
            targets = source_conf.get('targets', [])
            if targets:
                t = targets[0]
                summary_target_id = t
            else:
                self.logger.warning(f"No target found for summary of source {source_id}")
                return False

        # Parse Target ID / Topic
        target_chat_id = None
        target_topic_id = None
        
        if isinstance(summary_target_id, int):
             target_chat_id = summary_target_id
        elif isinstance(summary_target_id, str):
             if '.' in summary_target_id:
                 p = summary_target_id.split('.')
                 target_chat_id = int(p[0])
                 target_topic_id = int(p[1])
             else:
                 target_chat_id = int(summary_target_id)
        
        if not target_chat_id:
            return False

        # Prepare Content for AI
        formatted_lines = []
        
        # Load focus users from config
        focus_users = set()
        raw_focus = self.summary_config.get('focus_users', [])
        for u in raw_focus:
            focus_users.add(str(u))
            
        # Resolve Sender Names dynamically (to avoid polluting backup files)
        sender_ids = set()
        for m in msgs:
            sid = m.get('sender_id')
            if sid: sender_ids.add(int(sid))
            
        sender_map = {}
        if sender_ids and self.client:
            try:
                users = await self.client.get_entity(list(sender_ids))
                if not isinstance(users, list): users = [users]
                
                for u in users:
                    name = getattr(u, 'first_name', '') or ''
                    if getattr(u, 'last_name', None):
                        name += f" {u.last_name}"
                    sender_map[u.id] = name.strip() or "Unknown"
            except Exception as e:
                self.logger.warning(f"Failed to resolve sender names for summary: {e}")

        for m in msgs:
            clean_source_id = str(source_id)
            if clean_source_id.startswith("-100"):
                clean_source_id = clean_source_id[4:]
            
            real_src_id = m.get('_source_msg_id', m['id'])
            link = f"https://t.me/c/{clean_source_id}/{real_src_id}"
            
            text_content = m.get('text', '')
            
            sender_id = m.get('sender_id')
            if sender_id in current_focus_set:
                text_content = f"【重点关注用户发言】 {text_content}"
            
            if len(text_content) > 500:
                text_content = text_content[:500] + "..."
            
            # Check for followed user
            sender_id_raw = m.get('sender_id')
            sender_id = str(sender_id_raw) if sender_id_raw else ''
            
            sender_name = sender_map.get(sender_id_raw, 'Unknown') if sender_id_raw else 'Unknown'
            
            is_followed = sender_id in focus_users
            
            msg_header = f"Msg: {text_content}"
            if is_followed:
                msg_header = f"Msg (Followed User {sender_name}): {text_content}"
            elif sender_name and sender_name != 'Unknown':
                 msg_header = f"Msg ({sender_name}): {text_content}"
                
            formatted_lines.append(f"{msg_header}\nSourceLink: {link}\n---")

        context_text = "\n".join(formatted_lines)
        if not context_text.strip():
            return True

        # Prompt
        group_tag = source_conf.get('tag', '')
        # Fix date format for tags (YYYY_MM_DD)
        date_str = datetime.now().strftime('%Y_%m_%d')
        
        custom_prompt = self.summary_config.get('prompt')
        
        # Always append emphasis instruction if custom prompt is used
        if custom_prompt:
            emphasis = (
                "\n\nNote: Messages marked with '(Followed User ...)' are from high-priority users. "
                "You MUST give these users' messages higher weight in the summary. "
                "Explicitly mention their names and summarize what they discussed."
            )
            custom_prompt += emphasis
        
        summary_content = await self.provider.generate_summary(context_text, custom_prompt)
        if self._is_provider_error(summary_content):
            self.logger.error(f"Failed to generate summary for {source_id}: {summary_content}")
            return False
        
        # Build Final Message
        final_msg = f"#总结 {group_tag} #date_{date_str}\n\n{summary_content}"

        return await self._send_summary(
            target_chat_id=target_chat_id,
            target_topic_id=target_topic_id,
            source_id=source_id,
            file_key=file_key,
            group_tag=group_tag,
            date_str=date_str,
            final_msg=final_msg,
            summary_content=summary_content,
        )

    async def _send_summary(
        self,
        target_chat_id: int,
        target_topic_id: int | None,
        source_id: int | str,
        file_key: str,
        group_tag: str,
        date_str: str,
        final_msg: str,
        summary_content: str,
    ) -> bool:
        """Send a summary, falling back to a Markdown attachment when it is too long."""
        if len(final_msg) > TELEGRAM_MESSAGE_LIMIT:
            self.logger.warning(
                f"Summary for {source_id} is too long ({len(final_msg)} chars); using Markdown fallback"
            )
            return await self._send_long_summary_fallback(
                target_chat_id=target_chat_id,
                target_topic_id=target_topic_id,
                source_id=source_id,
                file_key=file_key,
                group_tag=group_tag,
                date_str=date_str,
                summary_content=summary_content,
            )

        try:
            await self._send_rendered_message(
                target_chat_id,
                final_msg,
                reply_to=target_topic_id,
            )
            self.logger.info(f"Sent summary for {source_id} to {target_chat_id}")
            return True
        except Exception as e:
            if self._is_message_too_long_error(e):
                self.logger.warning(
                    f"Summary for {source_id} exceeded Telegram limit during send; using Markdown fallback"
                )
                return await self._send_long_summary_fallback(
                    target_chat_id=target_chat_id,
                    target_topic_id=target_topic_id,
                    source_id=source_id,
                    file_key=file_key,
                    group_tag=group_tag,
                    date_str=date_str,
                    summary_content=summary_content,
                )

            self.logger.error(f"Failed to send summary: {e}", exc_info=True)
            return False

    async def _send_long_summary_fallback(
        self,
        target_chat_id: int,
        target_topic_id: int | None,
        source_id: int | str,
        file_key: str,
        group_tag: str,
        date_str: str,
        summary_content: str,
    ) -> bool:
        """Attach the full Markdown summary and send a shorter second-pass summary."""
        try:
            md_path = self._write_markdown_summary(
                source_id=source_id,
                file_key=file_key,
                group_tag=group_tag,
                date_str=date_str,
                summary_content=summary_content,
            )
            condensed_content = await self._generate_condensed_summary(summary_content)
            if self._is_provider_error(condensed_content):
                self.logger.error(f"Failed to generate condensed summary for {source_id}: {condensed_content}")
                condensed_content = (
                    "完整总结已生成，但二次压缩失败。请查看 Markdown 附件获取完整内容。"
                )
            condensed_msg = (
                f"#总结 {group_tag} #date_{date_str}\n\n"
                f"{condensed_content}\n\n"
                "完整总结过长，已保存为 Markdown 附件。"
            )
            condensed_msg = self._trim_for_telegram(condensed_msg)

            await self._send_rendered_message(
                target_chat_id,
                condensed_msg,
                reply_to=target_topic_id,
            )
            await self.client.send_file(
                target_chat_id,
                str(md_path),
                caption=f"#总结 {group_tag} #date_{date_str}\n完整 Markdown 总结",
                reply_to=target_topic_id,
            )
            self.logger.info(f"Sent condensed summary and Markdown attachment for {source_id} to {target_chat_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send long-summary fallback: {e}", exc_info=True)
            return False

    async def _send_rendered_message(
        self,
        target_chat_id: int,
        message: str,
        reply_to: int | None = None,
    ) -> None:
        """Send message text with Telegram Markdown rendering, falling back to plain text."""
        try:
            await self.client.send_message(
                target_chat_id,
                message,
                reply_to=reply_to,
                link_preview=False,
                parse_mode='md',
            )
        except Exception as e:
            if not self._is_markdown_parse_error(e):
                raise

            self.logger.warning(f"Markdown parse failed; sending plain text instead: {e}")
            await self.client.send_message(
                target_chat_id,
                message,
                reply_to=reply_to,
                link_preview=False,
            )

    async def _generate_condensed_summary(self, summary_content: str) -> str:
        prompt = (
            "你会收到一份已经生成的 Telegram 群组每日总结。请把它再次压缩成适合 Telegram "
            "单条消息发送的简短版本。\n"
            "要求：\n"
            "1. 使用中文输出。\n"
            "2. 保留最重要的主题、结论、行动项、风险和重点关注用户发言。\n"
            "3. 尽量保留关键 SourceLink，但不要为每个细节都保留链接。\n"
            "4. 控制在 2500 个中文字符以内。\n"
            "5. 不要提及你在压缩总结。"
        )
        return await self.provider.generate_summary(summary_content, prompt)

    def _write_markdown_summary(
        self,
        source_id: int | str,
        file_key: str,
        group_tag: str,
        date_str: str,
        summary_content: str,
    ) -> Path:
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        safe_source_id = self._safe_filename(str(source_id))
        safe_file_key = self._safe_filename(file_key.removesuffix(".bak"))
        md_path = self.summary_dir / f"{safe_file_key}_{safe_source_id}_summary.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 总结 {group_tag} #date_{date_str}\n\n")
            f.write(f"- Source ID: `{source_id}`\n")
            f.write(f"- Backup file: `{file_key}`\n")
            f.write(f"- Generated at: `{datetime.now().isoformat()}`\n\n")
            f.write(summary_content)
            f.write("\n")

        return md_path

    def _safe_filename(self, value: str) -> str:
        return "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in value).strip("_") or "summary"

    def _trim_for_telegram(self, text: str) -> str:
        if len(text) <= TELEGRAM_SAFE_MESSAGE_LIMIT:
            return text

        suffix = "\n\n[内容仍过长，已截断；完整版本见 Markdown 附件。]"
        return text[:TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix)] + suffix

    def _is_message_too_long_error(self, error: Exception) -> bool:
        err_text = str(error).lower()
        return "message was too long" in err_text or "message_too_long" in err_text

    def _is_markdown_parse_error(self, error: Exception) -> bool:
        err_text = str(error).lower()
        return (
            "can't parse" in err_text
            or "parse" in err_text and "entities" in err_text
            or "entityboundsinvalid" in err_text
            or "entity bounds invalid" in err_text
        )

    def _is_provider_error(self, content: str | None) -> bool:
        if not content:
            return True

        return content.startswith("Error generating summary:")

    async def run_batch_backfill(self):
        """Check all .bak files and process if missing."""
        if not self.enabled:
            return
            
        self.logger.info("Starting summary scan...")
        # Get all daily files
        for file_path in self.data_dir.glob("*_daily.bak"):
             if file_path.name in self.processed_files:
                 continue

             # Look for metadata file
             meta_path = file_path.with_suffix('.bak.meta')
             target_id = None
             
             if meta_path.exists():
                 try:
                     with open(meta_path, 'r') as f:
                         meta = json.load(f)
                         target_id = meta.get('target_id')
                 except:
                     pass
             
             if not target_id:
                 target_id = self._infer_target_id(file_path)

             if target_id:
                 await self.run_process(file_path, target_id)
             else:
                 self.logger.warning(f"Could not determine target ID for {file_path}")

    def _infer_target_id(self, file_path):
        try:
            messages_to_check = []
            with open(file_path, 'r') as f:
                for _ in range(5):
                    line = f.readline()
                    if line:
                        messages_to_check.append(json.loads(line))
            
            if not messages_to_check: return None
            
            candidates = {}
            for msg in messages_to_check:
                mid = msg['id']
                for (tid, r_mid) in self.mapper.reverse_mapping.keys():
                    if r_mid == mid:
                        candidates[tid] = candidates.get(tid, 0) + 1
            
            if candidates:
                best_tid = max(candidates, key=candidates.get)
                if candidates[best_tid] > 0:
                     return best_tid
        except:
            pass
        return None
