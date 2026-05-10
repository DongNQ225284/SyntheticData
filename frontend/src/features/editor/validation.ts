import type { AssetInventory, TemplateV2, ValidationIssue, ValidationResult } from "../../types/contracts";

const anchors = new Set([
  "top_left",
  "top_center",
  "top_right",
  "center_left",
  "center",
  "center_right",
  "bottom_left",
  "bottom_center",
  "bottom_right"
]);

export function validateTemplateLocal(template: TemplateV2, inventory: AssetInventory): ValidationResult {
  const issues: ValidationIssue[] = [];
  const classNames = new Set(inventory.classes.map((item) => item.name));
  const subtypesMap = new Map(inventory.classes.map((item) => [item.name, new Set(item.subtypes.map((sub) => sub.name))]));

  if (template.version !== 2) {
    issues.push({ severity: "error", path: "version", message: "Template version must be 2." });
  }

  if (!template.background_scenes.length) {
    issues.push({ severity: "error", path: "background_scenes", message: "background_scenes must be a non-empty list" });
  }

  let totalBlocks = 0;
  const weights = template.background_scenes.map((scene) => scene.scene_weight);
  template.background_scenes.forEach((scene, sceneIndex) => {
    const scenePath = `background_scenes[${sceneIndex}]`;
    if (scene.scene_weight <= 0) {
      issues.push({ severity: "error", path: `${scenePath}.scene_weight`, message: "scene_weight must be > 0" });
    }
    if (scene.canvas_size_range.width[0] > scene.canvas_size_range.width[1]) {
      issues.push({ severity: "error", path: `${scenePath}.canvas_size_range.width`, message: "min must be <= max" });
    }
    if (scene.canvas_size_range.height[0] > scene.canvas_size_range.height[1]) {
      issues.push({ severity: "error", path: `${scenePath}.canvas_size_range.height`, message: "min must be <= max" });
    }
    if (!scene.blocks.length) {
      issues.push({ severity: "warning", path: `${scenePath}.blocks`, message: "scene has zero blocks" });
    }
    scene.blocks.forEach((block, blockIndex) => {
      totalBlocks += 1;
      const blockPath = `${scenePath}.blocks[${blockIndex}]`;
      const [x, y, width, height] = block.bbox;
      if (x < 0 || x > 1 || y < 0 || y > 1) {
        issues.push({ severity: "error", path: `${blockPath}.bbox`, message: "x and y must be in [0, 1]" });
      }
      if (width <= 0 || height <= 0) {
        issues.push({ severity: "error", path: `${blockPath}.bbox`, message: "w and h must be > 0" });
      }
      if (x + width > 1 || y + height > 1) {
        issues.push({ severity: "error", path: `${blockPath}.bbox`, message: "bbox must stay inside the page" });
      }
      if (width <= 0.03 || height <= 0.03) {
        issues.push({ severity: "warning", path: `${blockPath}.bbox`, message: "bbox is very small" });
      }
      if (!classNames.has(block.class)) {
        issues.push({ severity: "error", path: `${blockPath}.class`, message: `class '${block.class}' not found in inventory` });
      }
      const knownSubtypes = subtypesMap.get(block.class) ?? new Set<string>();
      block.allowed_subtypes.forEach((subtype) => {
        if (!knownSubtypes.has(subtype)) {
          issues.push({
            severity: "error",
            path: `${blockPath}.allowed_subtypes`,
            message: `subtype '${subtype}' does not belong to class '${block.class}'`
          });
        }
      });
      if (!block.allowed_subtypes.length) {
        issues.push({ severity: "warning", path: `${blockPath}.allowed_subtypes`, message: "allowed_subtypes is empty" });
      }
      if (block.capacity < 1 || block.capacity > 10) {
        issues.push({ severity: "error", path: `${blockPath}.capacity`, message: "capacity must be integer in 1..10" });
      }
      if (block.skip_prob < 0 || block.skip_prob >= 1) {
        issues.push({ severity: "error", path: `${blockPath}.skip_prob`, message: "skip_prob must satisfy 0 <= value < 1" });
      } else if (block.skip_prob > 0.75) {
        issues.push({ severity: "warning", path: `${blockPath}.skip_prob`, message: "skip_prob is very high" });
      }
      if (block.position_anchor !== null && !anchors.has(block.position_anchor)) {
        issues.push({ severity: "error", path: `${blockPath}.position_anchor`, message: "invalid position_anchor" });
      }
      if (block.augmentation.rotation_max < 0 || block.augmentation.blur_max < 0 || block.augmentation.noise_max < 0) {
        issues.push({ severity: "error", path: `${blockPath}.augmentation`, message: "augmentation values must be >= 0" });
      }
    });
  });

  if (weights.length > 1) {
    const maxWeight = Math.max(...weights);
    const minWeight = Math.min(...weights);
    if (minWeight > 0 && maxWeight / minWeight >= 10) {
      issues.push({ severity: "warning", path: "background_scenes", message: "scene weights are very imbalanced" });
    }
  }

  if (totalBlocks === 0) {
    issues.push({ severity: "warning", path: "background_scenes", message: "whole template has zero blocks" });
  }

  return {
    issues,
    has_error: issues.some((issue) => issue.severity === "error"),
    has_warning: issues.some((issue) => issue.severity === "warning")
  };
}
