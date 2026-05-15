# FOFA API 接口文档

**文档来源**: [https://fofa.info/api](https://fofa.info/api)
**接口功能**: 提供搜索主机、获取详细网络空间测绘资产信息的方法，便于开发者进行自动化集成。

---

## 1. 基础信息

* **请求接口**: `https://fofa.info/api/v1/search/all`
* **请求方式**: `GET`
* **数据返回格式**: JSON

---

## 2. 请求参数 (Parameters)

在发起 GET 请求时，支持以下 URL 查询参数：

| 序号 | 参数名 | 是否必填 | 数据类型 | 描述说明 | 示例值 |
| :--- | :--- | :---: | :--- | :--- | :--- |
| 1 | `qbase64` | **是** | `string` | 经过 base64 编码后的查询语法（即在 FOFA 搜索框中输入的查询内容）。 | `aXA9IjEwMy4zNS4xNjguMzgi` |
| 2 | `fields` | 否 | `string` | 指定需要返回的资产字段，多个字段用逗号隔开。默认为 `host,ip,port`。 | `host,ip,port,title` |
| 3 | `page` | 否 | `int` | 翻页页码。默认为第 `1` 页，按照资产更新时间排序。 | `1` |
| 4 | `size` | 否 | `int` | 每页查询返回的数据条数。默认为 `100` 条，最大支持 `10,000` 条/页。 | `100` |
| 5 | `full` | 否 | `boolean` | 搜索时间范围。默认为 `false`（只搜索一年内的数据），指定为 `true` 即可搜索全部历史数据。 | `false` |
| 6 | `r_type` | 否 | `string` | 可以指定返回 `json` 格式的数据。 | `json` |

---

## 3. 请求示例 (Examples)

**使用 cURL 发起请求：**

```bash
curl -X GET "[https://fofa.info/api/v1/search/all?key=your_api_key&qbase64=dGl0bGU9ImJpbmci](https://fofa.info/api/v1/search/all?key=your_api_key&qbase64=dGl0bGU9ImJpbmci)"
```

*(注：`dGl0bGU9ImJpbmci` 是 `title="bing"` 的 base64 编码)*

**JSON 响应示例：**

JSON

```
{
  "error": false,               // 是否出现错误
  "consumed_fpoint": 0,         // 应扣F点
  "required_fpoints": 0,        // 实扣F点
  "size": 244569,               // 查询匹配到的总资产数量
  "page": 1,                    // 当前所在页码
  "mode": "extended",
  "query": "title=\"bing\"",    // 解析后的真实查询语句
  "results": [                  // 查询结果数组，顺序与 fields 参数指定的一致
    [
      "[https://bingchillin.org](https://bingchillin.org)",
      "172.67.213.134",
      "443"
    ],
    [
      "bingchillin.org",
      "104.21.69.223",
      "80"
    ]
  ]
}
```

------

## 4. 附录：支持查询返回的字段列表 (`fields`)

您可以在请求的 `fields` 参数中自由组合以下字段。请注意不同字段对应的会员权限要求。

### ⚠️ 使用限制与注意事项

1. 当 `fields` 查询包含 `cert` 或 `banner` 时，`size` 参数值最大限制为 **2000**。
2. 当 `fields` 查询包含 `body` 时，`size` 参数值最大限制为 **500**。

### 字段说明清单

| **序号** | **字段名 (fields)** | **描述**                                       | **账号权限要求** |
| -------- | ------------------- | ---------------------------------------------- | ---------------- |
| 1        | `ip`                | IP 地址                                        | 无               |
| 2        | `port`              | 端口                                           | 无               |
| 3        | `protocol`          | 协议名                                         | 无               |
| 4        | `country`           | 国家代码                                       | 无               |
| 5        | `country_name`      | 国家名                                         | 无               |
| 6        | `region`            | 区域                                           | 无               |
| 7        | `city`              | 城市                                           | 无               |
| 8        | `longitude`         | 地理位置经度                                   | 无               |
| 9        | `latitude`          | 地理位置纬度                                   | 无               |
| 10       | `asn`               | ASN 编号                                       | 无               |
| 11       | `org`               | ASN 组织                                       | 无               |
| 12       | `host`              | 主机名                                         | 无               |
| 13       | `domain`            | 域名                                           | 无               |
| 14       | `os`                | 操作系统                                       | 无               |
| 15       | `server`            | 网站 server (如 nginx, apache)                 | 无               |
| 16       | `icp`               | ICP 备案号                                     | 无               |
| 17       | `title`             | 网站标题                                       | 无               |
| 18       | `jarm`              | JARM 指纹                                      | 无               |
| 19       | `header`            | 网站 HTTP Header                               | 无               |
| 20       | `banner`            | 协议 Banner 信息                               | 无               |
| 21       | `cert`              | 证书内容                                       | 无               |
| 22       | `base_protocol`     | 基础协议，例如 tcp/udp                         | 无               |
| 23       | `link`              | 资产的完整 URL 链接                            | 无               |
| 24       | `cert.issuer.org`   | 证书颁发者组织                                 | 无               |
| 25       | `cert.issuer.cn`    | 证书颁发者通用名称                             | 无               |
| 26       | `cert.subject.org`  | 证书持有者组织                                 | 无               |
| 27       | `cert.subject.cn`   | 证书持有者通用名称                             | 无               |
| 28       | `tls.ja3s`          | JA3S 指纹信息                                  | 无               |
| 29       | `tls.version`       | TLS 协议版本                                   | 无               |
| 30       | `cert.sn`           | 证书的序列号 (New)                             | 无               |
| 31       | `cert.not_before`   | 证书生效时间                                   | 无               |
| 32       | `cert.not_after`    | 证书到期时间                                   | 无               |
| 33       | `cert.domain`       | 证书中的根域名                                 | 无               |
| 34       | `status_code`       | HTTP 状态码                                    | 无               |
| 35       | `header_hash`       | HTTP/HTTPS 响应信息计算的 hash 值              | 个人版及以上     |
| 36       | `banner_hash`       | 协议响应信息的完整 hash 值 (New)               | 个人版及以上     |
| 37       | `banner_fid`        | 协议响应信息架构的指纹值 (New)                 | 个人版及以上     |
| 38       | `cname`             | 域名 CNAME                                     | 专业版本及以上   |
| 39       | `lastupdatetime`    | FOFA 最后更新时间                              | 专业版本及以上   |
| 40       | `product`           | 产品名                                         | 专业版本及以上   |
| 41       | `product_category`  | 产品分类                                       | 专业版本及以上   |
| 42       | `product.version`   | 产品版本号 (Beta)                              | 商业版本及以上   |
| 43       | `icon_hash`         | 返回的 icon_hash 值                            | 商业版本及以上   |
| 44       | `cert.is_valid`     | 证书是否有效                                   | 商业版本及以上   |
| 45       | `cname_domain`      | CNAME 的域名                                   | 商业版本及以上   |
| 46       | `body`              | 网站正文内容                                   | 商业版本及以上   |
| 47       | `cert.is_match`     | 证书颁发者和持有者是否相同                     | 商业版本及以上   |
| 48       | `cert.is_equal`     | 证书和域名是否匹配 (New)                       | 商业版本及以上   |
| 49       | `icon`              | icon 图标                                      | 企业会员         |
| 50       | `fid`               | FID                                            | 企业会员         |
| 51       | `structinfo`        | 结构化信息 (部分协议支持，如 elastic, mongodb) | 企业会员         |