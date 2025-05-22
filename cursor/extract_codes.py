import re

def extract_referral_code(line):
    # Extract the code after "code=" from the URL
    match = re.search(r'code=([A-Z0-9]+)', line)
    if match:
        return match.group(1)
    return None

def process_file(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                for line in infile:
                    code = extract_referral_code(line)
                    code = "https://cursor.com/referral?code=" + extract_referral_code(line)
                    if code:
                        outfile.write(f"{code}\n")
        print(f"Processing complete. Codes saved to {output_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    input_file = "cusor_pro.txt"  # The file contains the URLs
    output_file = "cursor_codes.txt"  # Output file for the extracted codes
    
    process_file(input_file, output_file) 