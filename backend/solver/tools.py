import requests
from urllib.parse import urljoin
import re
import docker
import tarfile
import io

_docker_client = docker.from_env()

def make_execute_tool(workspace_dir:str):
    """
    Returns an execute_python_code function bound to a specific host workspace
    directory, which is mounted into every container spawned by this function --
    so files written in one call are visible in the next call within the same run.
    """
     
    def execute_python_code(code: str):
        """
        Execute arbitrary Python code inside an isolated, network-enabled sandbox
        container and return its stdout/stderr. Use this for -- custom headers, cookies, hashing, encoding/
        decoding, parsing complex responses, or any bespoke logic you need to write.
        The 'requests' and 'bs4' libraries are pre-installed.
        """
        container = None
        try:
            container = _docker_client.containers.run(
                "ctf-sandbox",
                command=["python3", "-c", code],
                detach=True,
                network_mode="bridge",   # allow outbound network -- needed to hit CTF targets
                mem_limit="256m",        # hard resource cap
                nano_cpus=1_000_000_000, # cap at 1 CPU core
                remove=False,            # we remove manually after reading logs
                volumes={workspace_dir: {"bind":"/workspace","mode":"rw"}},
                working_dir="/workspace"
            )
            result = container.wait(timeout=30)  # hard timeout on execution
            logs = container.logs(stdout=True, stderr=True).decode(errors="replace")
            return {
                "exit_code": result.get("StatusCode"),
                "output": logs[:1500],  # cap output size fed back to the LLM
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    return execute_python_code

def fetch_page(url:str , username: str = None, password: str = None) -> dict: 

    """
    Fetch a URL and return its status code , headers , and HTML content - First basic step
    If the target requires HTTP Basic Auth, pass username and password.
    """

    try :
        auth = (username, password) if username and password else None
        resp=requests.get(url,timeout=15,auth=auth)

        return {
            "url":url,
            "status_code":resp.status_code,
            "headers":dict(resp.headers),
            "html_snippet": resp.text[:2000],
        }
    
    except requests.RequestException as e:
        
        return {"url":url, "error":str(e)}


def check_path(base_url:str,path:str ,username: str = None, password: str = None) -> dict: 

    """
    to check for some specific path if it exists on the target
    """

    full_url = urljoin(base_url, path)
    auth = (username, password) if username and password else None
    try:
        resp = requests.get(full_url, timeout=15,auth=auth)
        return {"path": path, "status_code": resp.status_code, "url": full_url}
    except requests.RequestException as e:
        return {"path": path, "error": str(e)}



def extract_links(html:str) -> dict: 

    """
    Extract href/src links and any HTML comments from a page's HTML using regex to find urls inside href or src
    """

    links=re.findall(r'href=["\']([^"\']+)["\']|src=["\']([^"\']+)["\']',html)
    flat_links=list(set([l for pair in links for l in pair if l]))
    comments=re.findall(r'<!--(.*?)-->',html,re.DOTALL)
    return {"links":flat_links[:20],"comments":comments[:10]}




# Add this at the bottom of tools.py

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a URL and return its status code, headers, and HTML content (truncated). Use this first on any new URL to see what's there.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                    "username": {"type": "string", "description": "HTTP Basic Auth username, if the target requires login"},
                    "password": {"type": "string", "description": "HTTP Basic Auth password, if the target requires login"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_path",
            "description": "Check whether a specific path exists on the target, e.g. '/admin' or '/.git/HEAD'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "description": "The base URL of the target"},
                    "path": {"type": "string", "description": "The path to check, e.g. '/admin'"},
                    "username": {"type": "string", "description": "HTTP Basic Auth username, if the target requires login"},
                    "password": {"type": "string", "description": "HTTP Basic Auth password, if the target requires login"}
                },
                "required": ["base_url", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_links",
            "description": "Extract href/src links and HTML comments from a page's HTML content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {"type": "string", "description": "The raw HTML content to parse"}
                },
                "required": ["html"],
            },
        },
    },
]

TOOL_MAP = {
    "fetch_page": fetch_page,
    "check_path": check_path,
    "extract_links": extract_links,
}

EXECUTE_CODE_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": (
                "Execute Python code in an isolated sandbox with 'requests' and 'bs4' "
                "pre-installed, plus internet access. Use it to fetch pages, inspect "
                "headers/cookies, set custom headers, parse HTML, decode/hash data, "
                "or any other logic needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The Python code to execute"}
                },
                "required": ["code"],
            },
        },
    }
]

