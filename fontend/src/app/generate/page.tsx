"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const STEPS = [
  { key: "scene", label: "场景信息" },
  { key: "style", label: "风格模板" },
  { key: "confirm", label: "确认生成" },
] as const;

export default function WizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    scene_id: "",
    scene_name: "",
    min_score: 60,
    style_template: "premium",
  });

  const update = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleGenerate = () => {
    const params = new URLSearchParams({
      context: JSON.stringify({
        scene_id: form.scene_id,
        scene_name: form.scene_name,
        min_score: form.min_score,
        style_template: form.style_template,
      }),
    });
    router.push(`/generate/monitor?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border p-6">
        {/* Stepper */}
        <div className="flex items-center mb-8">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  i <= step ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-500"
                }`}
              >
                {i + 1}
              </div>
              <span className="ml-2 text-sm hidden sm:block">{s.label}</span>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-2 ${i < step ? "bg-blue-600" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Scene */}
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">场景标识</label>
              <input
                className="w-full border rounded-lg px-3 py-2"
                placeholder="如: SCENE_001"
                value={form.scene_id}
                onChange={(e) => update("scene_id", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">场景名称</label>
              <input
                className="w-full border rounded-lg px-3 py-2"
                placeholder="如: XX大厦消防方案"
                value={form.scene_name}
                onChange={(e) => update("scene_name", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">特征分值下限</label>
              <input
                type="number"
                className="w-full border rounded-lg px-3 py-2"
                value={form.min_score}
                onChange={(e) => update("min_score", Number(e.target.value))}
              />
            </div>
            <button
              className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700"
              onClick={() => setStep(1)}
            >
              下一步
            </button>
          </div>
        )}

        {/* Step 2: Style */}
        {step === 1 && (
          <div className="space-y-4">
            <label className="block text-sm font-medium mb-2">写作风格模板</label>
            {["premium", "standard", "concise"].map((tpl) => (
              <label key={tpl} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="style"
                  checked={form.style_template === tpl}
                  onChange={() => update("style_template", tpl)}
                />
                <span className="text-sm capitalize">{tpl}</span>
              </label>
            ))}
            <div className="flex gap-2">
              <button
                className="flex-1 border py-2 rounded-lg hover:bg-gray-50"
                onClick={() => setStep(0)}
              >
                上一步
              </button>
              <button
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700"
                onClick={() => setStep(2)}
              >
                下一步
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
              <div><span className="text-gray-500">场景标识：</span>{form.scene_id}</div>
              <div><span className="text-gray-500">场景名称：</span>{form.scene_name}</div>
              <div><span className="text-gray-500">分值下限：</span>{form.min_score}</div>
              <div><span className="text-gray-500">风格模板：</span>{form.style_template}</div>
            </div>
            <div className="flex gap-2">
              <button
                className="flex-1 border py-2 rounded-lg hover:bg-gray-50"
                onClick={() => setStep(1)}
              >
                上一步
              </button>
              <button
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700"
                onClick={handleGenerate}
              >
                开始生成
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
