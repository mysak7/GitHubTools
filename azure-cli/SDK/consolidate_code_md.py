import os

# Configuration
# Extensions to include

EXTENSIONS = {'.md'}
# Specific filenames to include
INCLUDE_FILES = {'Dockerfile', 'docker-compose.yml'}
# Directories to exclude
IGNORE_DIRS = {'.git', '.github', '__pycache__', '.terraform', 'logs', 'venv', 'env'}
# Output filename
OUTPUT_FILE = 'full_codebase_context_md.txt'

def collect_code(root_dir, output_file):
    count = 0
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Filter directories in-place to prevent recursion into ignored dirs
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
                
                for filename in filenames:
                    ext = os.path.splitext(filename)[1]
                    
                    if ext in EXTENSIONS or filename in INCLUDE_FILES:
                        filepath = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(filepath, root_dir)
                        
                        # Skip the output file itself if it's in the list (unlikely with .txt ext but good practice)
                        if filename == OUTPUT_FILE:
                            continue

                        # Skip this script itself
                        if filename == os.path.basename(__file__):
                            continue

                        print(f"Processing: {rel_path}")
                        
                        # Write clear delimiters for the LLM
                        outfile.write(f"\n{'='*80}\n")
                        outfile.write(f"FILE START: {rel_path}\n")
                        outfile.write(f"{'='*80}\n\n")
                        
                        try:
                            with open(filepath, 'r', encoding='utf-8') as infile:
                                content = infile.read()
                                outfile.write(content)
                        except UnicodeDecodeError:
                            outfile.write("[BINARY FILE OR ENCODING ERROR - SKIPPED CONTENT]")
                        except Exception as e:
                            outfile.write(f"[ERROR READING FILE: {str(e)}]")
                            
                        outfile.write(f"\n\n{'='*80}\n")
                        outfile.write(f"FILE END: {rel_path}\n")
                        outfile.write(f"{'='*80}\n")
                        count += 1
                        
        print(f"\nSuccess! Consolidated {count} files into '{output_file}'")

    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Output file path in the same directory
    output_path = os.path.join(script_dir, OUTPUT_FILE)

    collect_code(script_dir, output_path)
