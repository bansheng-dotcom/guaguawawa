# Closing 范例

## 范例 1

这有可能就是某个数据分析师的一个普通的早晨，我们同时在这一篇文章中看出：分析思路、分析方法、工作流程、具体代码等。当然，这是工作中的一小部分，下一期渭河预计将分享从产品角度继续讲解订单，对于订单这件事情来说，有非常多的篇幅可以讲~

---

## 范例 2

SELECT 
  wk.year_week,
  COUNT(CASE WHEN o.order_status = 1 THEN 1 END) as single_pay_rides,
  COUNT(CASE WHEN o.order_status = 2 THEN 1 END) as pass_rides,
  COUNT(DISTINCT o.order_id) as total_orders,
  COUNT(DISTINCT CASE WHEN p.card_name LIKE '%月卡%' THEN o.order_id END) as monthly_pass_orders,
  COUNT(DISTINCT CASE WHEN p.card_name LIKE '%连续包月卡%' THEN o.order_id END) as continuous_monthly_pass_orders,
  COUNT(DISTINCT CASE WHEN g.location_type = '核心' THEN o.order_id END) as core_location_or

---

## 范例 3

我更觉得大家应该养成分析的习惯，这种习惯是不依赖数据进行的逻辑推理，当你有这个习惯后，你才更容易培养所谓的数据敏感度。因为是否能很快的从数据里看出问题，依赖上面我提到的那种思考模式。当接触一个陌生的领域的时候，能够很快的摸到所有问题的重点，最后这些数据在你眼里也变成了一个个具体的点，而非一堆毫无意义的表和数据。

---

## 范例 4

欢迎大家在评论区交流指正，以及是否这些思路有优化的空间，欢迎建言献策。另外的就是，如果你有朋友也想了解这些内容，欢迎推荐给他们哦~

---

## 范例 5

--按工作日和周末统计订单
SELECT CASE WHEN DAYOFWEEK(date) IN (2,3,4,5,6) THEN '工作日' ELSE '周末' END AS day_type, SUM(order_num) AS total_orders
FROM table_name
GROUP BY CASE WHEN DAYOFWEEK(date) IN (2,3,4,5,6) THEN '工作日' ELSE '周末' END

---

