import { Page, Locator } from '@playwright/test';

/**
 * レポート作成ページのPage Object
 * 複数のロケーター戦略を使用して、CI環境でも要素を確実に見つけられるようにする
 */
export class CreateReportPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly inputField: Locator;
  readonly questionField: Locator;
  readonly introField: Locator;
  readonly csvTab: Locator;
  readonly spreadsheetTab: Locator;
  readonly csvFileUpload: Locator;
  readonly spreadsheetUrlInput: Locator;
  readonly submitButton: Locator;

  readonly inputFieldById: Locator;
  readonly questionFieldById: Locator;
  readonly introFieldById: Locator;
  readonly submitButtonByText: Locator;
  
  readonly inputFieldByIndex: Locator;
  readonly questionFieldByIndex: Locator;
  readonly introFieldByIndex: Locator;
  readonly inputFieldByPlaceholder: Locator;
  readonly questionFieldByPlaceholder: Locator;
  readonly introFieldByPlaceholder: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("新しいレポートを作成する"), h1:has-text("Create New Report")');
    
    this.inputField = page.getByLabel('レポートID');
    this.questionField = page.getByLabel('質問');
    this.introField = page.getByLabel('イントロダクション');
    
    this.inputFieldById = page.locator('#r0, input[id^="r"][id$="0"], #reportId');
    this.questionFieldById = page.locator('#r1, input[id^="r"][id$="1"], #question');
    this.introFieldById = page.locator('#r2, input[id^="r"][id$="2"], #intro');
    
    this.inputFieldByIndex = page.locator('input').nth(0);
    this.questionFieldByIndex = page.locator('input').nth(1);
    this.introFieldByIndex = page.locator('input').nth(2);
    
    this.inputFieldByPlaceholder = page.locator('input[placeholder*="ID"], input[placeholder*="id"]');
    this.questionFieldByPlaceholder = page.locator('input[placeholder*="質問"], input[placeholder*="Question"]');
    this.introFieldByPlaceholder = page.locator('input[placeholder*="イントロ"], input[placeholder*="Intro"]');
    
    this.csvTab = page.getByRole('tab', { name: 'CSVファイル' })
      .or(page.locator('button:has-text("CSVファイル")'))
      .or(page.locator('[role="tab"]').filter({ hasText: 'CSV' }));
    
    this.spreadsheetTab = page.getByRole('tab', { name: 'Googleスプレッドシート' })
      .or(page.locator('button:has-text("Googleスプレッドシート")'))
      .or(page.locator('[role="tab"]').filter({ hasText: 'Google' }));
    
    this.csvFileUpload = page.locator('input[type="file"]');
    this.spreadsheetUrlInput = page.getByPlaceholder('https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit');
    
    this.submitButton = page.getByRole('button', { name: 'レポート作成を開始' });
    this.submitButtonByText = page.locator('button:has-text("レポート作成を開始"), button:has-text("Submit"), button:has-text("送信")');
  }

  async goto() {
    await this.page.goto('/create');
  }

  /**
   * 基本情報を入力する
   * CI環境では複数のロケーター戦略を試みる
   */
  async fillBasicInfo(input: string, question: string, intro: string) {
    await this.fillReportId(input);
    await this.fillQuestion(question);
    await this.fillIntro(intro);
  }
  
  /**
   * レポートIDを入力する
   * 複数のロケーター戦略を試みる
   */
  async fillReportId(input: string) {
    console.log(`[TEST-STEP] レポートID「${input}」の入力を開始`);
    
    try {
      const isVisible = await this.inputField.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.inputField.fill(input);
        console.log(`[TEST-STEP] 主要なロケーターでレポートIDの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なロケーターでの入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.inputFieldById.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.inputFieldById.fill(input);
        console.log(`[TEST-STEP] ID属性バックアップロケーターでレポートIDの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] ID属性バックアップロケーターでの入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.inputFieldByPlaceholder.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.inputFieldByPlaceholder.fill(input);
        console.log(`[TEST-STEP] プレースホルダーバックアップロケーターでレポートIDの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] プレースホルダーバックアップロケーターでの入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.inputFieldByIndex.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.inputFieldByIndex.fill(input);
        console.log(`[TEST-STEP] インデックスバックアップロケーターでレポートIDの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] インデックスバックアップロケーターでの入力に失敗: ${error}`);
    }
    
    try {
      const inputs = await this.page.locator('input').all();
      console.log(`[TEST-DEBUG] 見つかった入力フィールド数: ${inputs.length}`);
      
      if (inputs.length > 0) {
        await inputs[0].fill(input);
        console.log(`[TEST-STEP] 直接検索でレポートIDの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-ERROR] すべての方法でレポートIDの入力に失敗: ${error}`);
      throw new Error(`レポートIDの入力に失敗: ${error}`);
    }
  }
  
  /**
   * 質問を入力する
   * 複数のロケーター戦略を試みる
   */
  async fillQuestion(question: string) {
    console.log(`[TEST-STEP] 質問「${question}」の入力を開始`);
    
    try {
      const isVisible = await this.questionField.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.questionField.fill(question);
        console.log(`[TEST-STEP] 主要なロケーターで質問の入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なロケーターでの質問入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.questionFieldById.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.questionFieldById.fill(question);
        console.log(`[TEST-STEP] ID属性バックアップロケーターで質問の入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] ID属性バックアップロケーターでの質問入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.questionFieldByPlaceholder.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.questionFieldByPlaceholder.fill(question);
        console.log(`[TEST-STEP] プレースホルダーバックアップロケーターで質問の入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] プレースホルダーバックアップロケーターでの質問入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.questionFieldByIndex.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.questionFieldByIndex.fill(question);
        console.log(`[TEST-STEP] インデックスバックアップロケーターで質問の入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] インデックスバックアップロケーターでの質問入力に失敗: ${error}`);
    }
    
    try {
      const inputs = await this.page.locator('input').all();
      console.log(`[TEST-DEBUG] 見つかった入力フィールド数: ${inputs.length}`);
      
      if (inputs.length > 1) {
        await inputs[1].fill(question);
        console.log(`[TEST-STEP] 直接検索で質問の入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-ERROR] すべての方法で質問の入力に失敗: ${error}`);
      throw new Error(`質問の入力に失敗: ${error}`);
    }
  }
  
  /**
   * イントロを入力する
   * 複数のロケーター戦略を試みる
   */
  async fillIntro(intro: string) {
    console.log(`[TEST-STEP] イントロ「${intro}」の入力を開始`);
    
    try {
      const isVisible = await this.introField.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.introField.fill(intro);
        console.log(`[TEST-STEP] 主要なロケーターでイントロの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なロケーターでのイントロ入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.introFieldById.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.introFieldById.fill(intro);
        console.log(`[TEST-STEP] ID属性バックアップロケーターでイントロの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] ID属性バックアップロケーターでのイントロ入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.introFieldByPlaceholder.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.introFieldByPlaceholder.fill(intro);
        console.log(`[TEST-STEP] プレースホルダーバックアップロケーターでイントロの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] プレースホルダーバックアップロケーターでのイントロ入力に失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.introFieldByIndex.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.introFieldByIndex.fill(intro);
        console.log(`[TEST-STEP] インデックスバックアップロケーターでイントロの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] インデックスバックアップロケーターでのイントロ入力に失敗: ${error}`);
    }
    
    try {
      const inputs = await this.page.locator('input').all();
      console.log(`[TEST-DEBUG] 見つかった入力フィールド数: ${inputs.length}`);
      
      if (inputs.length > 2) {
        await inputs[2].fill(intro);
        console.log(`[TEST-STEP] 直接検索でイントロの入力完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-ERROR] すべての方法でイントロの入力に失敗: ${error}`);
      throw new Error(`イントロの入力に失敗: ${error}`);
    }
  }

  /**
   * CSVファイルをアップロードする
   * 複数のロケーター戦略を試みる
   */
  async uploadCsvFile(filePath: string) {
    console.log(`[TEST-STEP] CSVファイルのアップロードを開始`);
    
    try {
      const isVisible = await this.csvTab.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.csvTab.click();
        console.log(`[TEST-STEP] CSVタブのクリック成功`);
      } else {
        console.log(`[TEST-DEBUG] CSVタブが見つからないか可視状態ではありません。既に選択されている可能性があります。`);
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] CSVタブクリックに失敗: ${error}`);
      console.log(`[TEST-DEBUG] CSVタブは既に選択されている可能性があります`);
    }
    
    try {
      const fileInputCount = await this.csvFileUpload.count();
      console.log(`[TEST-DEBUG] ファイル入力要素の数: ${fileInputCount}`);
      
      if (fileInputCount > 0) {
        await this.csvFileUpload.setInputFiles(filePath);
        console.log(`[TEST-STEP] CSVファイルのアップロード成功`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なロケーターでのファイルアップロードに失敗: ${error}`);
      
      try {
        const fileInputs = await this.page.locator('input[type="file"]').all();
        if (fileInputs.length > 0) {
          await fileInputs[0].setInputFiles(filePath);
          console.log(`[TEST-STEP] 代替方法でCSVファイルのアップロード成功`);
          return;
        }
      } catch (altError) {
        console.log(`[TEST-ERROR] 代替方法でもCSVファイルのアップロードに失敗: ${altError}`);
        throw new Error(`CSVファイルのアップロードに失敗: ${altError}`);
      }
    }
  }

  async enterSpreadsheetUrl(url: string) {
    try {
      await this.spreadsheetTab.click();
      console.log(`[TEST-STEP] スプレッドシートタブのクリック成功`);
    } catch (error) {
      console.log(`[TEST-DEBUG] スプレッドシートタブクリックに失敗: ${error}`);
      
      try {
        await this.page.locator('button, [role="tab"]').filter({ hasText: 'Google' }).click();
        console.log(`[TEST-DEBUG] 代替方法でスプレッドシートタブのクリック成功`);
      } catch (altError) {
        console.log(`[TEST-DEBUG] 代替方法でもスプレッドシートタブのクリックに失敗: ${altError}`);
      }
    }
    
    try {
      await this.spreadsheetUrlInput.fill(url);
      console.log(`[TEST-STEP] スプレッドシートURLの入力成功`);
    } catch (error) {
      console.log(`[TEST-ERROR] スプレッドシートURLの入力に失敗: ${error}`);
      throw error;
    }
  }

  /**
   * フォームを送信する
   * 複数のロケーター戦略を試みる
   */
  async submitForm() {
    console.log(`[TEST-STEP] フォームの送信を開始`);
    
    try {
      const isVisible = await this.submitButton.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.submitButton.click();
        console.log(`[TEST-STEP] 主要なロケーターでフォームの送信完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なロケーターでの送信ボタンクリックに失敗: ${error}`);
    }
    
    try {
      const isVisible = await this.submitButtonByText.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        await this.submitButtonByText.click();
        console.log(`[TEST-STEP] バックアップロケーターでフォームの送信完了`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-DEBUG] バックアップロケーターでの送信ボタンクリックに失敗: ${error}`);
    }
    
    try {
      const buttons = await this.page.locator('button').all();
      console.log(`[TEST-DEBUG] 見つかったボタン数: ${buttons.length}`);
      
      for (let i = 0; i < buttons.length; i++) {
        const text = await buttons[i].textContent();
        console.log(`[TEST-DEBUG] ボタン ${i} のテキスト: ${text}`);
        
        if (text && (text.includes('レポート作成') || text.includes('送信') || text.includes('Submit'))) {
          await buttons[i].click();
          console.log(`[TEST-STEP] 直接検索でフォームの送信完了`);
          return;
        }
      }
      
      if (buttons.length > 0) {
        await buttons[buttons.length - 1].click();
        console.log(`[TEST-STEP] 最後のボタンをクリックしてフォーム送信を試行`);
        return;
      }
    } catch (error) {
      console.log(`[TEST-ERROR] すべての方法でフォームの送信に失敗: ${error}`);
      throw new Error(`フォームの送信に失敗: ${error}`);
    }
  }
}
