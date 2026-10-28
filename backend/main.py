"""后端启动入口。

用法（在 backend 目录下）：

    python main.py                 # 开发模式，默认 0.0.0.0:8000，自动重载
    uvicorn app.main:app --reload   # 等价写法
    RELOAD=0 python main.py         # 关闭热重载（生产环境建议）

实际应用实例位于 app/main.py；本文件只负责按环境变量启动 uvicorn，
避免与旧版扁平路由（backend/routers）混用导致接口不一致。
"""

import os

import uvicorn

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "1") not in {"0", "false", "False"}

if __name__ == "__main__":
    print(f"专家库考试助手后端启动：http://{HOST}:{PORT}  (reload={RELOAD})")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
