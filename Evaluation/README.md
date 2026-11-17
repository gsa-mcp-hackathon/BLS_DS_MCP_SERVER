README

IBM Cloud had mandatory API Key rotations on Monday 16 Nov 2026 at 1pm ET

→ this will make it very difficult for anyone who has not already done so to:

    access to watsonx.ai

    create a project in wx.ai

    get LLMaaS working already 



In this shared folder are working credentials, a test script, and a modified mcp-eval-wxai skill to run MCP Tool evaluations with the Phoenix Arize Harness using the wx.ai platform to power the LLMs as a judge.


    copy and paste the variables in Credentials.txt into your local .env file

    copy and paste the wxai_sdk_test.py script and run it pointing at your local .env file to confirm your LLM access

    invoke the mcp-eval-wxai skill to setup your Phoenix evaluation harness using watsonx.ai models

        first, under .agents/skills, create a new folder called “mcp-eval-wxai” and copy the SKILL.md file into that new folder

        then it should be visible and accessible to your Bob agent