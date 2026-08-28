"""Search indexed support documents by semantic similarity."""

import argparse

from app.rag.retriever import semantic_search


def main() -> None:
	parser = argparse.ArgumentParser(description="Search the ChromaDB support-document index.")
	parser.add_argument("query", nargs="+", help="Question or phrase to search for")
	parser.add_argument("--limit", type=int, default=None, help="Maximum results to return")
	parser.add_argument("--min-score", type=float, default=None, help="Minimum relevance score from 0 to 1")
	args = parser.parse_args()

	for index, result in enumerate(semantic_search(" ".join(args.query), args.limit, args.min_score), start=1):
		metadata = result.document.metadata
		print(f"\n[{index}] relevance={result.relevance_score:.4f}")
		print(f"source={metadata.get('source')} type={metadata.get('document_type')}")
		location = metadata.get("page_number") or metadata.get("slide_number") or metadata.get("row_number")
		if location is not None:
			print(f"location={location}")
		print(result.document.page_content.strip())


if __name__ == "__main__":
	main()