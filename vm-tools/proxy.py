def response(flow):
    if "proxy.individual.githubcopilot.com/chat/completions" in flow.request.pretty_url:
        with open("C:/Users/studyuser/proxy.txt", "ab") as ofile:
            ofile.write(flow.request.pretty_url.encode())

            if flow.response.content:
                ofile.write(flow.response.content)

            ofile.write(b"\n---------------------------------------------------------------\n")