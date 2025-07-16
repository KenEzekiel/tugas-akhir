import { Search } from "@/components/search";
import { ResultsList } from "@/components/results-list";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-2 text-gray-800 dark:text-gray-100">
          Smart Contract Discovery System
        </h1>
        <p className="text-center mb-8 text-gray-600 dark:text-gray-300">
          Search for smart contracts using natural language
        </p>

        <Search />

        <div className="mt-8">
          <ResultsList />
        </div>
      </div>
    </main>
  );
}
