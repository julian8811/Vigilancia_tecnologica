import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies default variant classes", () => {
    const { container } = render(<Badge>Default</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-primary");
  });

  it("applies custom variant classes", () => {
    const { container } = render(<Badge variant="destructive">Danger</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-destructive");
  });

  it("applies project-status variant classes", () => {
    const { container } = render(<Badge variant="draft">Draft</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("bg-yellow-100");
  });

  it("accepts additional className", () => {
    const { container } = render(<Badge className="extra-class">Styled</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("extra-class");
  });

  it("renders as a div element", () => {
    render(<Badge>Tag</Badge>);
    const badge = screen.getByText("Tag");
    expect(badge.tagName).toBe("DIV");
  });
});
