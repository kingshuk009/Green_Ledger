import argparse
import dashboard_server
import uvicorn

ap=argparse.ArgumentParser(description="Run GreenLedger Carbon Asset dashboard")
ap.add_argument("--module0",default="http://127.0.0.1:8000")
ap.add_argument("--host",default="127.0.0.1")
ap.add_argument("--port",type=int,default=8010)
a=ap.parse_args()
dashboard_server.MODULE0_URL=a.module0
uvicorn.run(dashboard_server.app,host=a.host,port=a.port)
