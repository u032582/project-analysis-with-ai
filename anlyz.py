import os
import fnmatch
import json
import time
import logging
from pydantic import BaseModel, ValidationError
from langchain_community.chat_models import ChatOpenAI
from dotenv import load_dotenv


# 環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not found. Please set it before running the script.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileContent(BaseModel):
    content: str
    additional_kwargs: dict
    response_metadata: dict
    type: str
    name: str | None = None
    id: str
    example: bool = False
    tool_calls: list = []
    invalid_tool_calls: list = []
    usage_metadata: dict | None = None

def read_ignore_file(folder_path, filename):
    """
    Reads the specified ignore file and returns a list of patterns to ignore.
    """
    file_path = os.path.join(folder_path, filename)
    patterns = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            patterns = [line.strip() for line in file if line.strip() and not line.startswith('#')]
    return patterns

def read_gitignore_setting(folder_path):
    """
    Reads the .gitignore file in the specified folder and returns a list of patterns to ignore.
    """
    patterns = read_ignore_file(folder_path, '.gitignore')
    # Add patterns for files starting with a dot and containing "ignore"
    patterns.append('.*ignore*')
    return patterns

def should_ignore(path, patterns):
    """
    Checks if the given path matches any of the ignore patterns.
    """
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def analyze_folder(folder_path):
    """
    Analyzes the folder structure, counting the number of files and directories,
    and calculating the total size of files.
    """
    num_files = 0
    num_dirs = 0
    total_size = 0
    structure = []

    global_ignore_patterns = read_ignore_file(folder_path, '.repodocignore')

    for root, dirs, files in os.walk(folder_path):
        # Ignore .git folders
        dirs[:] = [d for d in dirs if d != '.git']
        ignore_patterns = read_gitignore_setting(root) + global_ignore_patterns
        filtered_dirs = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
        filtered_files = [f for f in files if not should_ignore(os.path.join(root, f), ignore_patterns)]

        if filtered_dirs or filtered_files:
            structure.append((root, filtered_dirs, filtered_files, [], []))

        num_dirs += len(filtered_dirs)
        num_files += len(filtered_files)
        for file in filtered_files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)

        dirs[:] = filtered_dirs

    return {
        'folder_name': os.path.basename(folder_path),
        'num_files': num_files,
        'num_dirs': num_dirs,
        'total_size': total_size,
        'structure': structure
    }

def format_structure(structure):
    """
    Formats the folder structure into a readable string format.
    """
    lines = []
    for root, dirs, files, analyses, modified_time in structure:
        indent_level = root.count(os.sep)
        indent = ' ' * 4 * indent_level
        lines.append(f"{indent}{os.path.basename(root)}/")
        for index, f in enumerate(files):
            lines.append(f"{indent}    {f}")
            if index < len(analyses) and analyses[index]:
                analysis = analyses[index]
                if isinstance(analysis, str) and analysis == "NOT_ANALYZED":
                    lines.append(f"{indent}    ※解析対象外\n")
                elif isinstance(analysis, dict):
                    file_type = analysis.get('file_type', '---')
                    description = analysis.get('description', '---')
                    lines.append(f"{indent}    {file_type}")
                    lines.append(f"{indent}    {description}\n")
    return '\n'.join(lines)

def write_stats_to_file(stats, filename):
    """
    Writes the statistics to a JSON file.
    """
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(stats, file, indent=4, ensure_ascii=False)

def load_stats_file(filename):
    """
    Reads the statistics from a JSON file.
    """
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        logger.error(f"No saved stats file found at {filename}")
        return None

def get_token_count(content: str) -> int:
    """
    Calculates the number of tokens in the given content.
    This is a placeholder function. You should replace it with the actual implementation.
    """
    # Placeholder implementation: count words as tokens
    return len(content.split())

def estimate_cost_for_gpt4o_0806(input_tokens: int, output_tokens: int) -> float:
    """
    Estimate the cost for GPT-4o-0806 model usage.

    Args:
        input_tokens (int): Number of input tokens.
        output_tokens (int): Number of output tokens.

    Returns:
        float: Estimated cost in USD.
    """
    return (input_tokens / 1000) * 0.0025 + (output_tokens / 1000) * 0.01

def gpt_analyze(structure, structure_text):
    """
    Analyzes the folder structure using GPT and updates the structure with the analysis results.
    """
    logger.info("Analyzing structure...")
    logger.info(structure_text)
    logger.info("====")

    total_input_tokens = 0
    total_output_tokens = 0
    flag_yesall = False

    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7, openai_api_key=openai_api_key)

    for root, dirs, files, analyses, modified_time in structure:
        for index, file in enumerate(files):
            file_path = os.path.join(root, file)
            logger.info(f"Analyzing file: {file_path}")
            try:
                last_modified_time = time.ctime(os.path.getmtime(file_path))

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                    if index < len(modified_time) and last_modified_time == modified_time[index]:
                        logger.info("Skip because this file has not been modified since the last analysis.")
                        choice = 'no'
                    elif flag_yesall:
                        choice = 'yes'
                    else:
                        choice = input("Do you want to start a new GPT analysis or skip this file? (yes/no or yesall)(y/n/a): ").strip().lower()
                        if choice in ['yesall', 'a']:
                            flag_yesall = True
                            choice = 'yes'

                    if choice in ['yes', 'y']:
                        logger.info("Starting GPT analysis...")

                        user_prompt = f"""
# Content of {file_path}:
{content}
"""

                        system_prompt = f"""
Analyze the given file name and file content, and extract the following information:

- type
Classification of the file as either code, config, or document

- file_type
Analysis result of the file content, such as whether the file is Java code, GitHub Actions YAML, etc.

- description
Write a brief summary of the file contents in Japanese.
For program code, describe the processing content and each function. (Refer to the sample description below)
For documents or configuration files, please explain the purpose of the file and provide additional details in bullet points if necessary. It does not need to be in Markdown title/section format.
Regardless of the type of text, please keep the content as concise as possible.
And please add appropriate bullet points and line breaks to make it easier to read.
**The description should be in Japanese.**

===== The overall file structure is as follows.
{structure_text}
"""

                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ]

                        try:
                            response = llm.invoke(messages)
                            logger.info(f"Analysis response: {json.dumps(response.model_dump(), indent=4, ensure_ascii=False)}")
                            if response:
                                result = FileContent.model_validate(response.model_dump())
                                if result:
                                    input_tokens = response.response_metadata['token_usage']['prompt_tokens']
                                    output_tokens = response.response_metadata['token_usage']['completion_tokens']
                                    total_input_tokens += input_tokens
                                    total_output_tokens += output_tokens

                                    for item in structure:
                                        if item[0] == root:
                                            item[3].append(result.dict())
                                            item[4].append(last_modified_time)
                                else:
                                    logger.error(f"Validation error while parsing response for {file_path}: Response: {json.dumps(response, indent=4, ensure_ascii=False)}")
                                    for item in structure:
                                        if item[0] == root:
                                            item[3].append("PARSE_ERROR")
                                            item[4].append(last_modified_time)
                            else:
                                logger.error(f"Unexpected response format from LLM: {response}")
                                for item in structure:
                                    if item[0] == root:
                                        item[3].append("FILE_READ_ERROR")
                                        item[4].append(last_modified_time)
                        except Exception as e:
                            logger.error(f"LLM invocation failed for {file_path}: {e}")
                            for item in structure:
                                if item[0] == root:
                                    item[3].append("LLM_INVOCATION_ERROR")
                                    item[4].append(last_modified_time)
                            raise
                        
            except Exception as e:
                logger.error(f"Could not read {file_path}: {e}")
                for item in structure:
                    if item[0] == root:
                        item[3].append("FILE_READ_ERROR")
                        item[4].append(last_modified_time)
                raise

    logger.info(f"Total input tokens: {total_input_tokens}")
    logger.info(f"Total output tokens: {total_output_tokens}")
    logger.info(f"Estimated cost (gpt-4o-08-06 global): ${estimate_cost_for_gpt4o_0806(total_input_tokens, total_output_tokens)}")

    return structure

if __name__ == "__main__":
    choice = input("""
*****************************************
**            REPO DOC  v0.9           **
*****************************************
Select an option:
    - Start a new analysis: (new)/(n)
    - Continue from an intermediate file: (inter)/(i)
    - Update the analysis with GPT *File update only: (update)/(u)
    - Confirm a final file: (final)/(f)
>""").strip().lower()
    stats_intermediate_filename = 'stats_intermediate.json'
    stats_final_filename = 'stats_final.json'

    if choice in ['new', 'n']:
        folder_path = input("Enter the folder path to analyze: ")
        folder_path = os.path.abspath(folder_path)
        stats = analyze_folder(folder_path)

        structure_text = format_structure(stats['structure'])
        logger.info("====")
        logger.info(structure_text)

        user_input = input("Is the structure OK? (yes/no): ").strip().lower()
        if user_input in ['yes', 'y']:
            write_stats_to_file(stats, stats_intermediate_filename)
            logger.info(f"Stats have been written to {stats_intermediate_filename}")
        else:
            logger.info("Stats were not written to file.")

    if choice in ['new', 'n', 'inter', 'i']:
        stats = load_stats_file(stats_intermediate_filename)
        if stats:
            structure_text = format_structure(stats['structure'])
            logger.info("====")
            logger.info(structure_text)
            stats['structure'] = gpt_analyze(stats['structure'], structure_text)
            write_stats_to_file(stats, stats_final_filename)

    if choice in ['update', 'u']:
        stats = load_stats_file(stats_final_filename)
        if stats:
            structure_text = format_structure(stats['structure'])
            logger.info("====")
            logger.info(structure_text)
            stats['structure'] = gpt_analyze(stats['structure'], structure_text)
            write_stats_to_file(stats, stats_final_filename)

    if choice in ['new', 'n', 'inter', 'i', 'final', 'f', 'update', 'u']:
        stats = load_stats_file(stats_final_filename)
        if stats:
            user_check = input("Check the result? (yes/no)(y/n): ").strip().lower()
            if user_check in ['yes', 'y']:
                structure_text = format_structure(stats['structure'])
                logger.info("========================")
                logger.info(structure_text)
    else:
        logger.error("Invalid choice. Please enter 'new', 'inter', 'update', or 'final'.")
