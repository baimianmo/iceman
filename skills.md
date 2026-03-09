# Skills Registry

```skill
{"name":"profile","description":"查询并返回客户画像（JSON 字符串）","entry":"skills.builtin.profile:ProfileSkill","methods":[{"name":"query_profile","args":[{"name":"name","type":"string"}],"returns":"string:json"}],"parameters":{"query_profile":{"type":"object","properties":{"name":{"type":"string","description":"客户姓名"}}}},"returns":{"query_profile":{"type":"string"}},"auto_load":true}
```

```skill
{"name":"card","description":"根据文案生成主题贺卡图片，返回图片路径","entry":"skills.builtin.card:CardSkill","methods":[{"name":"generate_card","args":[{"name":"content","type":"string"},{"name":"theme","type":"string"}],"returns":"string:path"}],"parameters":{"generate_card":{"type":"object","properties":{"content":{"type":"string"},"theme":{"type":"string","enum":["birthday","holiday","celebration","default"],"default":"default"}},"required":["content"]}},"returns":{"generate_card":{"type":"string"}},"auto_load":true}
```

```skill
{"name":"web_search","description":"通用 Web 检索（返回摘要列表）","type":"http","endpoint":"https://api.example.com/search","method":"GET","headers":{"Authorization":"Bearer ${API_TOKEN}"},"parameters":{"type":"object","properties":{"q":{"type":"string","description":"查询词"},"limit":{"type":"integer","default":5}},"required":["q"]},"returns":{"type":"object","properties":{"items":{"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"url":{"type":"string"},"snippet":{"type":"string"}}}}}},"auto_load":false}
```
