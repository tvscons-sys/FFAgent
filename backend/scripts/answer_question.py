"""Test the full retrieval-to-answer pipeline with Gemini generation."""

import argparse
import json

from app.rag.generator import answer_question


def main() -> None:
	parser = argparse.ArgumentParser(description="Answer a question using grounded Gemini generation.")
	parser.add_argument("query", nargs="+", help="Question to answer")
	parser.add_argument("--json", action="store_true", help="Output as JSON")
	args = parser.parse_args()

	query = " ".join(args.query)
	answer = answer_question(query)

	if args.json:
		print(json.dumps({
			"question": query,
			"answer": answer.text,
			"sources": answer.sources,
		}, indent=2))
	else:
		print(f"\nQuestion: {query}\n")
		print(f"Answer:\n{answer.text}\n")
		
		if answer.sources:
			print("Sources:")
			for source in answer.sources:
				print(f"  - {source['document']} ({source['type']}) [relevance: {source['relevance']:.2%}]")
				if 'location' in source:
					print(f"    location: {source['location']}")


if __name__ == "__main__":
	main()
