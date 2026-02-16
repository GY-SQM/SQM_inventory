# -*- coding: utf-8 -*-
"""
SQM v5.0.0 - 자동 스타일 적용기
=================================

모든 Treeview 위젯을 찾아서 자동으로 스타일 적용

사용법:
    from fixes.auto_style_applier import apply_styles_to_all_trees
    
    # 앱 초기화 완료 후 호출
    apply_styles_to_all_trees(root_widget)
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)


def find_all_treeviews(widget, trees=None):
    """
    위젯 트리를 재귀적으로 탐색하여 모든 Treeview 찾기
    
    Args:
        widget: 탐색할 루트 위젯
        trees: 발견된 Treeview 리스트 (재귀용)
    
    Returns:
        list: 모든 Treeview 위젯
    """
    if trees is None:
        trees = []
    
    # 현재 위젯이 Treeview인지 확인
    if isinstance(widget, ttk.Treeview):
        trees.append(widget)
    
    # 자식 위젯 재귀 탐색
    try:
        for child in widget.winfo_children():
            find_all_treeviews(child, trees)
    except (ValueError, TypeError, AttributeError, tk.TclError) as _e:
        logger.warning(f"Suppressed: {_e}")
    
    return trees


def apply_styles_to_all_trees(root_widget):
    """
    v5.0.0: 모든 Treeview에 통일 스타일 자동 적용
    
    Args:
        root_widget: 루트 위젯 (보통 self.root 또는 self.notebook)
    """
    try:
        from fixes.global_tree_style import apply_to_tree_immediately
        
        # 모든 Treeview 찾기
        trees = find_all_treeviews(root_widget)
        
        logger.info(f"✅ v5.0.0: {len(trees)}개 Treeview 발견")
        
        # 각 Treeview에 스타일 적용
        for i, tree in enumerate(trees):
            try:
                apply_to_tree_immediately(tree)
                logger.debug(f"  [{i+1}/{len(trees)}] 스타일 적용 완료")
            except (ValueError, TypeError, AttributeError, tk.TclError) as e:
                logger.warning(f"  [{i+1}/{len(trees)}] 스타일 적용 실패: {e}")
        
        logger.info(f"✅ v5.0.0: 모든 Treeview 스타일 적용 완료!")
        
    except ImportError as e:
        logger.error(f"스타일 모듈 로딩 실패: {e}")
    except (ValueError, TypeError, AttributeError, tk.TclError) as e:
        logger.error(f"자동 스타일 적용 실패: {e}")


__all__ = ['find_all_treeviews', 'apply_styles_to_all_trees']
