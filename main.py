import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-backend", choices=["deepseek", "ollama", "glm"], default=os.getenv("LLM_BACKEND", "deepseek"))
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"))
    parser.add_argument("--ollama-base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--glm-model", default=os.getenv("GLM_MODEL", "glm-4-flash"))
    parser.add_argument("--glm-api-key", default=os.getenv("GLM_API_KEY", ""))

    args, _ = parser.parse_known_args()
    os.environ["LLM_BACKEND"] = args.llm_backend
    if args.llm_backend == "ollama":
        os.environ["OLLAMA_MODEL"] = args.ollama_model
        os.environ["OLLAMA_BASE_URL"] = args.ollama_base_url
    elif args.llm_backend == "glm":
        os.environ["GLM_MODEL"] = args.glm_model
        if args.glm_api_key:
            os.environ["GLM_API_KEY"] = args.glm_api_key
    
    # 延迟导入，以便环境变量生效
    from agents import main_agent

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
