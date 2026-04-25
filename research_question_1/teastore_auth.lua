--[[
	Auth service isolated load test.
	Directly hits the auth REST API to test login/logout/cart operations.
	Services needed: registry + db + persistence + auth (port 8080 exposed)

	NOTE: Auth endpoints expect a SessionBlob JSON body for POST requests.
	The httploadgenerator sends simple GET/POST without custom JSON bodies,
	so this script tests the endpoints that can be reached with query params
	and minimal payloads. For full session-blob testing, consider a tool like
	Locust or JMeter that supports custom request bodies.

	This script focuses on the ready endpoint and lightweight calls.
	For a more realistic auth workload, use the WebUI-isolated test instead,
	which exercises auth through the WebUI's login/logout/cart servlets.
--]]

prefix = "http://debian.tail4a3387.ts.net:8083/tools.descartes.teastore.auth/rest/"
postIndex = {}

function onCycle()
	calls = {
		"ready/isready",
		"ready/isready",
		"ready/isready",
		"ready/isready",
	}
end

function onCall(callnum)
	if calls[callnum] == nil then
		return nil
	end
	return prefix..calls[callnum]
end

function isPost(index)
	for i = 1,#postIndex do
		if index == postIndex[i] then
			return true
		end
	end
	return false
end
