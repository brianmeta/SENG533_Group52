--[[
	WebUI service isolated load test.
	Same browsing pattern as teastore_browse.lua but targeting localhost.
	Services needed: ALL services (registry + db + persistence + auth + image + recommender + webui)
	This tests the full stack with WebUI as the entry point.
--]]

prefix = "http://debian.tail4a3387.ts.net:8080/tools.descartes.teastore.webui/"
productviewcount = 30
postIndex = {3, 11}

function onCycle()
	userpostfix = 1 + math.random(90)
	calls = {
	"",
	"login",
	--[[[POST]--]]"loginAction?username=user"..userpostfix.."&password=password",
	--[[[POST]--]]"category?page=1&category=",
	"product?id=",
	--[[[POST]--]]"cartAction?addToCart=&productid=",
	"category?page=1&category=",
	"category?page=",
	--[[[POST]--]]"cartAction?addToCart=&productid=",
	"profile",
	--[[[POST]--]]"loginAction?logout=",
	}
end

function onCall(callnum)
	if callnum == 2 then
		local categoryids = html.extractMatches("href=.*category.*?category=","\\d+","&page=1.")
		categoryid = categoryids[math.random(#categoryids)]
	elseif callnum == 5 then
		local productids = html.extractMatches("href=.*product.*?id=","\\d+",". ><img")
		productid = productids[math.random(#productids)]
		local pagecount = #html.getMatches(".*href=.*category.*?category=\\d+&page=\\d+.>\\d+</a></li>.*")
		page = math.random(pagecount)
	elseif callnum == 9 then
		local productids = html.extractMatches("href=.*product.*?id=","\\d+",". ><img")
		productid = productids[math.random(#productids)]
	end

	if calls[callnum] == nil then
		return nil
	elseif callnum == 4 then
		return "[POST]"..prefix..calls[callnum]..categoryid.."&number="..productviewcount
	elseif callnum == 5 then
		return prefix..calls[callnum]..productid
	elseif callnum == 6 then
		return "[POST]"..prefix..calls[callnum]..productid
	elseif callnum == 7 then
		return prefix..calls[callnum]..categoryid
	elseif callnum == 8 then
		return prefix..calls[callnum]..page.."&category="..categoryid
	elseif callnum == 9 then
		return "[POST]"..prefix..calls[callnum]..productid
	elseif isPost(callnum) then
		return "[POST]"..prefix..calls[callnum]
	else
		return prefix..calls[callnum]
	end
end

function isPost(index)
	for i = 1,#postIndex do
		if index == postIndex[i] then
			return true
		end
	end
	return false
end
