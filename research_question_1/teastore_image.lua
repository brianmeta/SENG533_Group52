--[[
	Image service isolated load test.
	Hits the image REST API to test image generation/serving performance.
	Services needed: registry + db + persistence + image (port 8080 exposed)

	NOTE: getProductImages and getWebImages expect POST with a JSON HashMap body.
	The httploadgenerator's POST support is limited to simple form-style posts.
	This script tests the GET endpoints (state, finished) for basic load.
	For full image-serving tests, use the WebUI-isolated test which triggers
	image loading through normal page rendering.
--]]

prefix = "http://debian.tail4a3387.ts.net:8084/tools.descartes.teastore.image/rest/"
postIndex = {}

function onCycle()
	calls = {
		"image/finished",
		"image/state",
		"image/finished",
		"image/state",
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
