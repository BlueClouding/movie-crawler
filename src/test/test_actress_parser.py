import json
import os
from datetime import datetime
from typing import List, Dict, Any

from common.enums.enums import SupportedLanguage


def parse_actress_json_to_sql(json_file_path: str) -> List[str]:
    """
    Parse actress JSON file and generate SQL insert commands for the actress table.
    
    Args:
        json_file_path: Path to the JSON file containing actress data
        
    Returns:
        List of SQL insert commands
    """
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file not found: {json_file_path}")
    
    # Read and parse JSON file
    with open(json_file_path, 'r', encoding='utf-8') as file:
        actresses_data = json.load(file)
    
    sql_commands = []
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    # Process each actress entry
    for actress in actresses_data:
        # Extract required fields with defaults for optional fields
        name = actress.get('name', '').replace("'", "''")  # Escape single quotes for SQL
        language = SupportedLanguage.JAPANESE.value  # Assuming 'ja' from filename
        avatar = actress.get('avatar_url', '').replace("'", "''") if 'avatar_url' in actress else None
        debut_year = actress.get('debut_year') if 'debut_year' in actress else None
        link = actress.get('detail_url', '').replace("'", "''") if 'detail_url' in actress else None
        
        # Build SQL insert command
        sql = f"INSERT INTO actresses (name, language, avatar, debut_year, link, create_time, update_time) VALUES "
        
        # Format values based on their types
        values = []
        values.append(f"'{name}'" if name else "NULL")
        values.append(f"'{language}'")
        values.append(f"'{avatar}'" if avatar else "NULL")
        values.append(f"{debut_year}" if debut_year is not None else "NULL")
        values.append(f"'{link}'" if link else "NULL")
        values.append(f"'{current_time}'")
        values.append(f"'{current_time}'")
        
        sql += f"({', '.join(values)});"
        sql_commands.append(sql)
    
    return sql_commands


def test_parse_actresses_json():
    """
    Test function to parse actresses JSON file and print SQL insert commands.
    """
    import glob
    # 处理 data 目录下所有 actresses_ja_page 开头的文件
    actresses_ja_page_files = glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 'data', 'actresses_ja_page_*.json'))
    
    try:
        all_sql_commands = []
        
        for actresses_ja_page_file in actresses_ja_page_files:
            sql_commands = parse_actress_json_to_sql(actresses_ja_page_file)
            all_sql_commands.extend(sql_commands)
            
            print(f"Generated {len(sql_commands)} SQL insert commands from {os.path.basename(actresses_ja_page_file)}.")
            # Print first 3 commands as examples
            for i, sql in enumerate(sql_commands[:3]):
                print(f"\nSQL {i+1}:")
                print(sql)
            
        # Write SQL commands to a file for execution
        output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 'data', 'actresses_insert.sql')
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write('\n'.join(all_sql_commands))
        print(f"\nTotal {len(all_sql_commands)} SQL commands written to {output_file}")
        print(f"Processed {len(actresses_ja_page_files)} files.")
        
        if not actresses_ja_page_files:
            print("\nNo files found matching the pattern 'actresses_ja_page_*.json' in the data/ directory.")
            print("Please check if the files exist and the path is correct.")
            print("Current search path: {}".format(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 'data')))

        
    except Exception as e:
        print(f"Error processing JSON file: {e}")


if __name__ == "__main__":
    test_parse_actresses_json()
