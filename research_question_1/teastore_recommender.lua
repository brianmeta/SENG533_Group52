--[[
	Recommender service isolated load test.
	Hits the recommender REST API to test recommendation computation performance.
	Services needed: registry + db + persistence + recommender (port 8080 exposed)

	NOTE: The /recommend endpoint expects a POST with a list of OrderItem objects.
	This script tests the GET endpoints (train readiness, timestamp) and the
	ready check. For full recommendation workload testing, use the WebUI-isolated
	test which triggers recommendations through product page rendering.
--]]

prefix = "http://debian.tail4a3387.ts.net:8081/tools.descartes.teastore.recommender/rest/"
postIndex = {}

function onCycle()
	calls = {
		"train/isready",
		"train/timestamp",
		"train/isready",
		"train/timestamp",
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
