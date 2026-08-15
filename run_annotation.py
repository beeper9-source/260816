import sys
import os
from mxl_parser import annotate_mxl

def main():
    if len(sys.argv) < 3:
        print("사용법: python run_annotation.py <입력파일.mxl 또는 .musicxml> <출력파일.mxl 또는 .musicxml>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"오류: 입력 파일 '{input_file}'을(를) 찾을 수 없습니다.")
        sys.exit(1)
        
    try:
        annotate_mxl(input_file, output_file)
        print(f"\n성공: 클래식 기타 운지 및 줄 번호 표기가 완료되어 '{output_file}'에 저장되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
