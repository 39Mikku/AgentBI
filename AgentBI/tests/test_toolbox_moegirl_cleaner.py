import unittest
from datetime import datetime, timezone

from AgentBI.src.services.toolbox.moegirl.cleaner import MoegirlMarkdownCleaner
from AgentBI.src.services.toolbox.moegirl.scraper import MoegirlPage


FIXED_TIME = datetime(2026, 7, 15, 12, 34, 56, tzinfo=timezone.utc)


class MoegirlMarkdownCleanerTests(unittest.TestCase):
    def test_regular_page_keeps_article_text_and_removes_noise(self):
        page = MoegirlPage(
            title="雷电芽衣",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="""<div><p>页首噪声</p><h2>简介</h2><p><a href="/x">角色正文</a></p>
              <img src="x.png"><h2>查 · 论 · 编</h2><p>模板噪声</p></div>""",
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertFalse(result.is_disambiguation)
        self.assertIn("角色正文", result.markdown)
        self.assertNotIn("/x", result.markdown)
        self.assertNotIn("页首噪声", result.markdown)
        self.assertNotIn("模板噪声", result.markdown)

    def test_regular_page_prefers_basic_information_before_introduction(self):
        page = MoegirlPage(
            title="雷电芽衣",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="""
            <div>
              <p>页首站点噪声</p>
              <table><tr><th>基本资料</th><td>姓名：雷电芽衣</td></tr></table>
              <h2>简介</h2><p>角色正文</p>
            </div>
            """,
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertIn("基本资料", result.markdown)
        self.assertIn("姓名：雷电芽衣", result.markdown)
        self.assertIn("简介", result.markdown)
        self.assertIn("角色正文", result.markdown)
        self.assertNotIn("页首站点噪声", result.markdown)

    def test_regular_page_removes_only_configured_noise_sections(self):
        page = MoegirlPage(
            title="雷电芽衣",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="""
            <div>
              <h2>简介</h2><p>开场正文</p>
              <h3>技能</h3><p>技能模板噪声</p><h4>技能子段</h4><p>子段噪声</p>
              <h3>经历</h3><p>经历正文必须保留</p>
              <h2>角色相关</h2><p>角色相关模板噪声</p><h3>关联条目</h3><p>关联噪声</p>
              <h2>轶事</h2><p>结尾正文必须保留</p>
            </div>
            """,
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertIn("开场正文", result.markdown)
        self.assertIn("经历正文必须保留", result.markdown)
        self.assertIn("结尾正文必须保留", result.markdown)
        self.assertNotIn("技能模板噪声", result.markdown)
        self.assertNotIn("子段噪声", result.markdown)
        self.assertNotIn("角色相关模板噪声", result.markdown)
        self.assertNotIn("关联噪声", result.markdown)

    def test_disambiguation_keeps_candidate_lists(self):
        page = MoegirlPage(
            title="芽衣",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=("消歧义页",),
            article_html='<p>可以指：</p><h2>作品人物</h2><ul><li><a href="/雷电芽衣">雷电芽衣</a></li></ul>',
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertTrue(result.is_disambiguation)
        self.assertIn("可以指", result.markdown)
        self.assertIn("雷电芽衣", result.markdown)

    def test_disambiguation_notice_is_detected_without_category(self):
        page = MoegirlPage(
            title="同名条目",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="<div><p>这是一个消歧义页，可以指：</p><ul><li>候选项</li></ul></div>",
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertTrue(result.is_disambiguation)
        self.assertIn("候选项", result.markdown)

    def test_noise_nodes_images_and_raw_urls_are_removed(self):
        page = MoegirlPage(
            title="测试条目",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="""
            <div>
              <h2>正文</h2><p>保留文本 https://tracking.example/path</p>
              <script>脚本噪声</script><style>样式噪声</style><nav>导航噪声</nav>
              <footer>页脚噪声</footer><span class="mw-editsection">编辑噪声</span>
              <ol class="references"><li>引用噪声</li></ol>
              <span class="reference">引用标记噪声</span>
              <div class="mw-references-wrap">引用区域噪声</div>
              <div class="navbox">导航盒噪声</div><img src="noise.png" alt="图片噪声">
            </div>
            """,
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertIn("保留文本", result.markdown)
        for noise in (
            "tracking.example",
            "脚本噪声",
            "样式噪声",
            "导航噪声",
            "页脚噪声",
            "编辑噪声",
            "引用噪声",
            "引用标记噪声",
            "引用区域噪声",
            "导航盒噪声",
            "图片噪声",
        ):
            self.assertNotIn(noise, result.markdown)

    def test_raw_url_removal_stops_at_adjacent_prose_delimiters(self):
        for delimiter in ("，", "。", "；", "！", "？", "、", "）", "】", ")", "]", ">"):
            with self.subTest(delimiter=delimiter):
                markdown = MoegirlMarkdownCleaner._normalize_markdown(
                    f"前文 https://example.com/path{delimiter}后文应保留"
                )

                self.assertEqual(markdown, f"前文 {delimiter}后文应保留")

    def test_raw_url_removal_consumes_balanced_ascii_parentheses(self):
        markdown = MoegirlMarkdownCleaner._normalize_markdown(
            "前文 https://example.com/Foo_(bar)，后文应保留"
        )

        self.assertEqual(markdown, "前文 ，后文应保留")

    def test_tables_and_attribution_are_preserved(self):
        page = MoegirlPage(
            title="测试条目",
            source_url="https://mzh.moegirl.org.cn/example",
            categories=(),
            article_html="<h2>数据</h2><table><tr><th>角色</th></tr><tr><td>芽衣</td></tr></table>",
        )

        result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)

        self.assertEqual(result.title, page.title)
        self.assertEqual(result.source_url, page.source_url)
        self.assertIn("# 测试条目", result.markdown)
        self.assertIn("角色", result.markdown)
        self.assertIn("芽衣", result.markdown)
        self.assertIn(page.source_url, result.markdown)
        self.assertIn(FIXED_TIME.isoformat(), result.markdown)


if __name__ == "__main__":
    unittest.main()
