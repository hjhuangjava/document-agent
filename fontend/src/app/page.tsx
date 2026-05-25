import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold">方案生成智能体</h1>
          <p className="text-gray-500 mt-2">数据驱动 · 风格模仿 · 一致性校验</p>
        </div>

        <div className="space-y-3">
          <Link
            href="/generate"
            className="block w-full bg-blue-600 text-white py-3 rounded-lg font-medium text-center hover:bg-blue-700"
          >
            用户方案生成
          </Link>

          <div className="grid grid-cols-2 gap-3">
            <Link
              href="/admin/skills"
              className="block border py-3 rounded-lg font-medium text-center hover:bg-white"
            >
              技能仓
            </Link>
            <Link
              href="/admin/canvas"
              className="block border py-3 rounded-lg font-medium text-center hover:bg-white"
            >
              编排画布
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
