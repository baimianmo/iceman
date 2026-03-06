import sys
from agents import main_agent

def main():
    print("Welcome to IceMan Customer Care System (CLI Version)")
    print("---------------------------------------------------")
    print("支持的指令示例：")
    print("1. 给张三发个生日祝福")
    print("2. 给李四发个春节祝福")
    print("3. 祝贺王五升职了")
    print("---------------------------------------------------")

    while True:
        try:
            user_input = input("\n请输入指令 (输入 'exit' 退出): ").strip()
            if user_input.lower() == 'exit':
                print("再见！")
                break
            
            if not user_input:
                continue

            main_agent.run(user_input)

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()