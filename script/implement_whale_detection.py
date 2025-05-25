import logging
import os
import sys
import re

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")


def update_predictor_with_whale_detection():
    """Update the SignalPredictor to incorporate whale detection"""
    log.info("Updating SignalPredictor to incorporate whale detection")

    # Locate the predictor file
    predictor_paths = [
        os.path.join(parent_dir, "model/predictor.py"),
        os.path.join(parent_dir, "predictors/predictor.py"),
        os.path.join(parent_dir, "models/predictor.py")
    ]

    predictor_file = None
    for path in predictor_paths:
        if os.path.exists(path):
            predictor_file = path
            break

    if not predictor_file:
        log.error("Could not find predictor file")
        return False

    try:
        # Read the file content
        with open(predictor_file, 'r') as f:
            content = f.read()

        # Check if whale detection is already imported
        if "from core.whale_detector import detect_whale_activity" not in content:
            # Add import
            import_section_end = content.find("\n\n", content.find("import"))
            if import_section_end == -1:
                import_section_end = content.find("\n", content.find("import"))

            import_statement = "\nfrom core.whale_detector import detect_whale_activity"
            content = content[:import_section_end] + \
                import_statement + content[import_section_end:]

        # Update indicator weights
        weights_pattern = r'self\.indicator_weights\s*=\s*{[^}]*}'
        weights_match = re.search(weights_pattern, content)

        if weights_match:
            old_weights = weights_match.group(0)

            # Check if whale_activity already exists
            if "whale_activity" not in old_weights:
                # Add whale activity
                new_weights = old_weights.replace(
                    "}", ',\n            "whale_activity": 0.15  # Add weight for whale activity\n        }')
                content = content.replace(old_weights, new_weights)

        # Update long and short conditions to include whale activity
        conditions_patterns = [
            r'long_conditions\s*=\s*\[[^\]]*\]',
            r'short_conditions\s*=\s*\[[^\]]*\]'
        ]

        for pattern in conditions_patterns:
            match = re.search(pattern, content)
            if match:
                old_conditions = match.group(0)

                if "whale_activity" not in old_conditions:
                    # Add whale activity to conditions
                    new_conditions = old_conditions.replace(
                        "]", ",\n                whale_activity  # Add whale activity\n            ]")
                    content = content.replace(old_conditions, new_conditions)

        # Update the _calculate_confidence method to boost confidence for whale activity
        confidence_method_pattern = r'def\s+_calculate_confidence\s*\([^)]*\):.*?(?=\n\s*def|\n\s*class|$)'
        confidence_match = re.search(
            confidence_method_pattern, content, re.DOTALL)

        if confidence_match:
            old_method = confidence_match.group(0)

            if "whale activity" not in old_method:
                # Find the section with boosts
                boost_section = re.search(
                    r'# For market conditions.*?(?=\n\s+# Additional chance|$)', old_method, re.DOTALL)

                if boost_section:
                    old_boost = boost_section.group(0)
                    indentation = re.search(
                        r'^(\s+)', old_boost.split('\n')[1]).group(1)

                    # Add whale boost
                    whale_boost = f"{old_boost}\n{indentation}# Extra boost when whale activity is present (last condition)\n{indentation}if conditions[-1]:  # If whale activity is detected\n{indentation}    preliminary_confidence += 10.0  # Significant boost for whale activity"
                    content = content.replace(old_boost, whale_boost)

                # Also update the exceptional boost section
                exceptional_section = re.search(
                    r'# Additional chance for exceptional signals.*?(?=\n\s+# Cap confidence|$)', content, re.DOTALL)

                if exceptional_section:
                    old_exceptional = exceptional_section.group(0)
                    indentation = re.search(
                        r'^(\s+)', old_exceptional.split('\n')[1]).group(1)

                    # Add whale exceptional boost
                    whale_exceptional = f"{indentation}# If we have whale activity AND other strong indicators\n{indentation}if conditions[-1] and true_count >= 4:  # Whale + 3 other indicators\n{indentation}    exceptional_boost = np.random.uniform(15, 25)  # Higher chance of 90%+\n{indentation}elif true_count >= 5:  # Many indicators agree"

                    # Replace the first elif condition
                    content = re.sub(r'if true_count >= 5:',
                                     whale_exceptional, content)

        # Update the signal dictionary to include whale activity
        signal_dict_pattern = r'signal\s*=\s*{[^}]*}'
        signal_match = re.search(signal_dict_pattern, content, re.DOTALL)

        if signal_match:
            old_signal = signal_match.group(0)

            if "whale_activity" not in old_signal:
                # Add whale activity to indicators used
                old_indicators = re.search(
                    r'"indicators_used":\s*"([^"]*)"', old_signal).group(0)
                new_indicators = old_indicators.replace(
                    '"', '"RSI, MACD, Volume, BB, S/R, Whale"')
                modified_signal = old_signal.replace(
                    old_indicators, new_indicators)

                # Add whale activity field
                modified_signal = modified_signal.replace(
                    "}", ',\n                "whale_activity": "Yes" if whale_activity else "No"\n            }')
                content = content.replace(old_signal, modified_signal)

        # Write the updated content back to the file
        with open(predictor_file, 'w') as f:
            f.write(content)

        log.info(
            f"Successfully updated {predictor_file} to incorporate whale detection")

        # Now update the telebot/sender.py file to show whale activity
        sender_file = os.path.join(parent_dir, "telebot/sender.py")

        if os.path.exists(sender_file):
            with open(sender_file, 'r') as f:
                sender_content = f.read()

            # Check if we need to update the message formation
            message_pattern = r'message\s*=\s*f".*?HIGH CONFIDENCE SIGNAL'
            message_match = re.search(message_pattern, sender_content)

            if message_match and "whale_emoji" not in sender_content:
                # Add whale emoji logic
                emoji_section = re.search(
                    r'emoji\s*=\s*".*?"\s*if\s*direction\s*==\s*"LONG".*?\n', sender_content)

                if emoji_section:
                    old_emoji = emoji_section.group(0)
                    indentation = re.search(r'^(\s+)', old_emoji).group(1)

                    # Add whale emoji
                    whale_emoji = f"{old_emoji}{indentation}# Add whale emoji if whale activity detected\n{indentation}whale_emoji = \"🐋 \" if signal.get('whale_activity') == \"Yes\" else \"\"\n"
                    sender_content = sender_content.replace(
                        old_emoji, whale_emoji)

                # Update message formation
                old_message = message_match.group(0)
                new_message = old_message.replace(
                    "*{emoji} ", "*{emoji} {whale_emoji}")
                sender_content = sender_content.replace(
                    old_message, new_message)

                # Add whale activity information to the message
                take_profit_section = re.search(
                    r'message\s*\+=\s*f"\*Take Profit 3.*?\n\n"', sender_content, re.DOTALL)

                if take_profit_section:
                    old_tp = take_profit_section.group(0)
                    indentation = re.search(
                        r'^(\s+)', old_tp.split('\n')[0]).group(1)

                    # Add whale info
                    whale_info = f"{old_tp}{indentation}# Add whale activity info if present\n{indentation}if signal.get('whale_activity') == \"Yes\":\n{indentation}    message += f\"*🐋 Whale Activity:* Detected\\n\"\n"
                    sender_content = sender_content.replace(old_tp, whale_info)

                # Write updated sender
                with open(sender_file, 'w') as f:
                    f.write(sender_content)

                log.info(
                    "Successfully updated Telegram sender to display whale activity")

        return True

    except Exception as e:
        log.error(f"Error updating predictor with whale detection: {str(e)}")
        return False


if __name__ == "__main__":
    update_predictor_with_whale_detection()
