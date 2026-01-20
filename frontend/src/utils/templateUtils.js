export function prevInterview(ctx) {
    if (ctx.currentSlideIndex > 0) {
        ctx.currentSlideIndex--;
        updateQuestion(ctx);
    }
}

export function nextInterview(ctx) {
    if (ctx.currentSlideIndex < ctx.interviewOptions.length - 1) {
        ctx.currentSlideIndex++;
        updateQuestion(ctx);
    }
}
    
export function updateQuestion(ctx) {
    // 将选中的长句赋给 selectedInstances[currentIndex].question
    if (ctx.selectedInstances[ctx.currentIndex]) {
        ctx.selectedInstances[ctx.currentIndex].question = ctx.displayedInterview;
    }
}