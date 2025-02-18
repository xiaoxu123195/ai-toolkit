const getChatToken = (uri: string, body: any, now: Date) => {
    const date = now.toUTCString();
    let data = {
        "Chat-Date": date,
        "Chat-Token": ""
    }
    let jsText = 'KGZ1bmN0aW9uKHBhcmFtcykge2xldCBtZXRob2QgPSBwYXJhbXMubWV0aG9kLGE9YWlzb19tZDUsYj1haXNvX2Jhc2U2NCxjPWFpc29fYWVzLGQ9YWlzb19oMjU2LGU9YWlzb19zaGExLHVyaSA9IHBhcmFtcy51cmksYWNjZXNzX3Rva2VuID0gcGFyYW1zLmFjY2Vzc190b2tlbixodHRwX3ZlcnNpb24gPSBwYXJhbXMuaHR0cF92ZXJzaW9uLGRhdGUgPSBwYXJhbXMuZGF0ZSx0b2tlbiA9IG1ldGhvZCArICIgIiArIHVyaSArICIgIiArIGh0dHBfdmVyc2lvbisiICIrImRhdGU6IisgIiAiICsgZGF0ZTt0b2tlbiA9IGEodG9rZW4pO3Rva2VuID0gZCh0b2tlbiwgYWNjZXNzX3Rva2VuKTt0b2tlbiA9IGEodG9rZW4pO3Rva2VuID0gYSh0b2tlbik7dG9rZW4gPSBkKHRva2VuLCBhY2Nlc3NfdG9rZW4pO3Rva2VuID0gYSh0b2tlbik7dG9rZW4gPSBiKHRva2VuKTt0b2tlbiA9IGEodG9rZW4pO3Rva2VuID0gYih0b2tlbik7dG9rZW4gPSBkKHRva2VuLCBhY2Nlc3NfdG9rZW4pO3JldHVybiB7dG9rZW46IHRva2VuICsgIkQxIitbMTIwLDY3LDExMyw5OSw2NiwxMDQsODEsNTAsNjUsMTE3LDY3LDExOSw5OCw4OCw4MCw2Niw4Nyw1MSwxMDMsODMsNjEsNDcsNDUsMTE2LDExNiw4NSw3MCw1MSwxMjAsODcsMTEzLDExOSw5MCw4NSwxMDQsMTE2LDU0LDU0LDc1LDc2LDc2LDExNCwxMTgsMTA5LDcyLDExOCwxMDcsMTIxLDc0LDExMywxMDgsMTE5LDEwMywxMDcsNjUsNzAsMTE1LDk5LDEwOSwxMTMsNTUsMTAxLDQzLDU3LDg5LDgzLDUwLDU1LDc0LDc3LDEyMCwxMTcsOTksNzEsNzgsNjYsMTE1LDQ5LDEwMywxMTgsNDMsMTEwLDg1LDc3LDcxLDEwNiw1NSwxMDIsMTE2LDY1LDcyLDcyLDExNSw3OCw5OSw3NCw5MCw0MywxMTYsNzcsOTcsMTE1LDgzLDU2LDEyMiwxMTMsODUsNTYsNzUsMTIyLDU1LDEwNCw2Nyw1NCw1MCwxMTgsMTE5LDg0LDQzLDExOSwxMjEsNjksODAsODgsNTUsOTgsNjgsODEsODEsMTE1LDg4LDczLDYxXS5tYXAociA9PiBTdHJpbmcuZnJvbUNoYXJDb2RlKHIpKS5qb2luKCIiKX19KQ==';
    try {
        jsText = atob(jsText).trim(),
            jsText += "(".concat(JSON.stringify({
                method: "POST",
                uri,
                access_token: nData.mid,//"25170478106281596142749210017392"
                http_version: "HTTP/1.1",
                date,
                body
            }), ")");
        const { token } = eval(jsText);
        data["Chat-Token"] = token
    } catch (a) {
        console.error(a);
        data["Chat-Token"] = "-2"
    }
    return data
}