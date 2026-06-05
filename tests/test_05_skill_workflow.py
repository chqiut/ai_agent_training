# -*- coding: utf-8 -*-
"""
实验5测试：Skill 工作流
=====================

测试 Skill 剧本系统：
- Skill 加载
- Skill 内容解析
- Skill 执行
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env

setup_test_env()


class TestSkillLoading:
    """测试 Skill 加载"""

    def test_skill_file_exists(self):
        """测试 Skill 文件存在"""
        skill_path = Path(__file__).parent.parent / "skills" / "industry_insight.md"
        assert skill_path.exists()

    def test_skill_content_format(self):
        """测试 Skill 内容格式"""
        skill_path = Path(__file__).parent.parent / "skills" / "industry_insight.md"

        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查基本结构
        assert "# Skill 剧本" in content
        assert "## 剧本描述" in content
        assert "## 适用场景" in content


class TestSkillRegistry:
    """测试 Skill 注册"""

    def test_available_skills(self):
        """测试可用 Skill 列表"""
        skills_dir = Path(__file__).parent.parent / "skills"
        skill_files = list(skills_dir.glob("*.md"))

        assert len(skill_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])