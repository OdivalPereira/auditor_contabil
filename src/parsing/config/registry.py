"""
Layout Registry

Manages loading and detection of bank layouts from JSON configuration files.
"""
import os
import json
import logging
from typing import List, Optional
from .layout import BankLayout, ColumnDef

logger = logging.getLogger(__name__)


class LayoutRegistry:
    """
    Registry for bank PDF layouts.
    
    Loads layout configurations from JSON files and provides
    automatic detection based on PDF text content.
    """
    
    def __init__(self, layouts_dir: str):
        """
        Initialize registry with path to layouts directory.
        
        Args:
            layouts_dir: Path to directory containing .json layout files
        """
        self.layouts_dir = layouts_dir
        self.layouts: List[BankLayout] = []
        self._load_layouts()

    def _load_layouts(self) -> None:
        """Scans the directory and loads all .json layouts."""
        if not os.path.exists(self.layouts_dir):
            logger.warning(f"Layouts directory not found: {self.layouts_dir}")
            return

        for fname in os.listdir(self.layouts_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.layouts_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.layouts.append(self._parse_layout(data))
                        logger.debug(f"Loaded layout: {fname}")
                except Exception as e:
                    logger.error(f"Error loading layout {fname}: {e}")

    def _parse_layout(self, data: dict) -> BankLayout:
        """Converts dict to BankLayout object."""
        columns = [ColumnDef(**c) for c in data.get('columns', [])]
        
        # Remove columns from data before unwrapping
        layout_data = data.copy()
        if 'columns' in layout_data:
            del layout_data['columns']
            
        return BankLayout(columns=columns, **layout_data)

    def detect(self, text: str) -> Optional[BankLayout]:
        """
        Detect the appropriate layout for the given PDF text.
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            First matching BankLayout, or None if no match
        """
        for layout in self.layouts:
            if all(k in text for k in layout.keywords):
                logger.debug(f"Detected layout: {layout.name}")
                return layout
        return None
    
    def get_by_name(self, name: str) -> Optional[BankLayout]:
        """Get layout by name."""
        for layout in self.layouts:
            if layout.name == name:
                return layout
        return None
    
    def list_layouts(self) -> List[str]:
        """List all available layout names."""
        return [l.name for l in self.layouts]

    def save_layout(self, layout_data: dict, filename: str = None) -> bool:
        """
        Save a new layout configuration to disk.
        
        Args:
            layout_data: Dictionary containing layout configuration
            filename: Optional filename. If None, generated from bank name.
            
        Returns:
            bool: True if saved successfully
        """
        try:
            if not filename:
                # Sanitize name for filename
                safe_name = "".join(c for c in layout_data.get('name', 'unknown') if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_').lower()
                filename = f"{safe_name}.json"
                
            fpath = os.path.join(self.layouts_dir, filename)
            
            # Save to file
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=4, ensure_ascii=False)
                
            # Reload layouts to include the new one
            self.layouts = []
            self._load_layouts()
            
            logger.info(f"Saved new layout to {fpath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False
